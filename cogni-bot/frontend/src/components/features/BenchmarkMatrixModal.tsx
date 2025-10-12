import React, { useEffect, useState } from "react";
import { X } from "lucide-react";
import { getBenchmarkDetails } from "../../services/api";

interface BenchmarkMatrixModalProps {
  open: boolean;
  onClose: () => void;
  chatbotId: string;
}

const BenchmarkMatrixModal: React.FC<BenchmarkMatrixModalProps> = ({ open, onClose, chatbotId }) => {
  const [matrix, setMatrix] = useState<any[][]>([]);
  const [llmTemps, setLlmTemps] = useState<string[]>([]);
  const [questions, setQuestions] = useState<any[]>([]);
  const [efficiencies, setEfficiencies] = useState<Record<string, number>>({});
  const [bestLlmTemp, setBestLlmTemp] = useState<string>("");
  const [bestEfficiency, setBestEfficiency] = useState<number>(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    getBenchmarkDetails(chatbotId)
      .then((res) => {
        const details = res.data.details || [];
        
        // Filter out incomplete data first
        const validDetails = details.filter((row: any) => 
          row.regen_llm_name && 
          row.regen_llm_name !== 'Unknown' && 
          row.regen_llm_name !== null && 
          row.regen_llm_name !== undefined &&
          row.regen_temperature !== null && 
          row.regen_temperature !== undefined &&
          row.generated_sql && 
          row.generated_sql !== null &&
          row.score !== null && 
          row.score !== undefined
        );

        // Get all unique LLM-temp combos from valid data only
        const uniqueLlmTemps = Array.from(
          new Set(
            validDetails.map((row: any) => `${row.regen_llm_name}-${row.regen_temperature}`)
          )
        ).sort() as string[];
        setLlmTemps(uniqueLlmTemps);

        // Get all unique questions (by question + original_sql) from valid data only
        const uniqueQuestions = Array.from(
          new Map(
            validDetails.map((row: any) => [
              `${row.generated_question}_${row.original_sql}`, 
              { question: row.generated_question, sql: row.original_sql }
            ])
          ).values()
        ).sort((a, b) => a.question.localeCompare(b.question)) as { question: string; sql: string }[];
        setQuestions(uniqueQuestions);

        // Build matrix: rows = questions, columns = llmTemps
        const matrixRows = uniqueQuestions.map((q) => {
          return uniqueLlmTemps.map((lt) => {
            const [llm, temp] = (lt as string).split("-");
            const found = validDetails.find(
              (row: any) =>
                row.generated_question === q.question &&
                row.original_sql === q.sql &&
                row.regen_llm_name === llm &&
                String(row.regen_temperature) === temp
            );
            return found ? (found.score === 1 ? "✔️" : "❌") : "";
          });
        });
        setMatrix(matrixRows);

        // Calculate efficiency for each LLM-temp
        const eff: Record<string, number> = {};
        uniqueLlmTemps.forEach((lt) => {
          const [llm, temp] = (lt as string).split("-");
          const rows = validDetails.filter(
            (row: any) => row.regen_llm_name === llm && String(row.regen_temperature) === temp
          );
          const correct = rows.filter((row: any) => row.score === 1).length;
          eff[lt as string] = rows.length > 0 ? correct / rows.length : 0;
        });
        setEfficiencies(eff);

        // Find best LLM-temp
        let best = "";
        let bestEff = 0;
        for (const [lt, val] of Object.entries(eff)) {
          if (val > bestEff) {
            best = lt;
            bestEff = val;
          }
        }
        setBestLlmTemp(best);
        setBestEfficiency(bestEff);
        setLoading(false);
      })
      .catch((error) => {
        console.error('Error loading benchmark matrix:', error);
        setLoading(false);
      });
  }, [open, chatbotId]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-5xl w-full mx-4 max-h-[80vh] overflow-y-auto p-6 relative">
        <button onClick={onClose} className="absolute top-2 right-2 p-2 text-gray-400 hover:text-gray-700"><X size={20} /></button>
        <h2 className="text-xl font-bold mb-4 text-[#1e3a8a]">Benchmark Matrix</h2>
        {loading ? (
          <div className="text-center py-10">Loading...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full border text-sm">
              <thead>
                <tr>
                  <th className="px-2 py-2 border-b bg-gray-50">NL Question</th>
                  <th className="px-2 py-2 border-b bg-gray-50">Original SQL</th>
                  {llmTemps.map((lt) => (
                    <th key={lt} className="px-2 py-2 border-b bg-gray-50 text-center">{lt}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {questions.map((q, i) => (
                  <tr key={i}>
                    <td className="px-2 py-2 border-b max-w-xs whitespace-pre-wrap">{q.question}</td>
                    <td className="px-2 py-2 border-b max-w-xs whitespace-pre-wrap font-mono text-xs">{q.sql}</td>
                    {matrix[i] && matrix[i].map((cell, j) => (
                      <td key={j} className="px-2 py-2 border-b text-center text-lg">{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={2} className="px-2 py-2 font-semibold text-right bg-gray-50">Best LLM to choose:</td>
                  {llmTemps.map((lt, idx) => (
                    <td
                      key={lt}
                      className={`px-2 py-2 font-semibold text-center bg-gray-50 ${lt === bestLlmTemp ? 'bg-green-100 text-green-800 border-2 border-green-400' : ''}`}
                    >
                      {lt === bestLlmTemp ? '⭐ ' : ''}{lt === bestLlmTemp ? bestLlmTemp : ''}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td colSpan={2} className="px-2 py-2 font-semibold text-right bg-gray-50">Best Efficiency:</td>
                  {llmTemps.map((lt, idx) => (
                    <td
                      key={lt}
                      className={`px-2 py-2 font-semibold text-center bg-gray-50 ${lt === bestLlmTemp ? 'bg-green-100 text-green-800 border-2 border-green-400' : ''}`}
                    >
                      {lt === bestLlmTemp ? `${Math.round(bestEfficiency * 100)}%` : `${Math.round((efficiencies[lt] || 0) * 100)}%`}
                    </td>
                  ))}
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default BenchmarkMatrixModal; 