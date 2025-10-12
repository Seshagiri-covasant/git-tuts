import json
import logging
from .llm_factory import get_llm
from ..utils.prompt_loader import get_prompt


def generate_chart_config(table_data, user_query, sql_query=None, chatbot_id=None, llm_name=None, temperature = None):
    """
    Generate Chart.js configuration for visualizing SQL query results,
    using the currently configured LLM for the chatbot.
    """
    try:
        llm = get_llm(llm_name=llm_name, temperature=temperature)

        prompt = get_prompt(
            "data_analysis/chart_generation.txt",
            user_query=user_query,
            sql_query=sql_query or "Not provided",
            table_data=json.dumps(table_data, indent=2)
        )

        response = llm.invoke(prompt)
        content = response.content if hasattr(
            response, 'content') else str(response)

        content = content.strip().lstrip('```json').rstrip('```').strip()

        chart_config = json.loads(content)

        if 'data' in chart_config and 'datasets' in chart_config['data']:
            for dataset in chart_config['data']['datasets']:
                if 'backgroundColor' not in dataset:
                    dataset['backgroundColor'] = _generate_colors(
                        len(chart_config['data'].get('labels', [])))

        return chart_config

    except json.JSONDecodeError:
        return _generate_fallback_chart(table_data, user_query)
    except Exception as e:
        logging.error(f"Error generating chart config: {e}", exc_info=True)
        return {"error": f"Error generating chart config: {str(e)}"}


def _generate_fallback_chart(table_data, user_query):
    """
    Generate a simple chart configuration using rule-based logic
    """
    if not table_data or len(table_data) == 0:
        return {"error": "No data to visualize"}

    # Get column names
    columns = list(table_data[0].keys()) if table_data else []
    if len(columns) < 2:
        return {"error": "Need at least 2 columns for visualization"}

    # Determine chart type based on data
    numeric_columns = []
    text_columns = []

    for col in columns:
        sample_values = [row.get(col)
                         for row in table_data[:5] if row.get(col) is not None]
        if sample_values and all(isinstance(v, (int, float)) or (isinstance(v, str) and v.replace('.', '').replace('-', '').isdigit()) for v in sample_values):
            numeric_columns.append(col)
        else:
            text_columns.append(col)

    # Chart configuration logic
    if len(text_columns) >= 1 and len(numeric_columns) >= 1:
        # Bar chart: categorical vs numeric
        label_col = text_columns[0]
        value_col = numeric_columns[0]

        labels = [str(row[label_col]) for row in table_data]
        values = [float(row[value_col]) if row[value_col]
                  is not None else 0 for row in table_data]

        return {
            "type": "bar",
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": value_col,
                    "data": values,
                    "backgroundColor": _generate_colors(len(labels)),
                    "borderWidth": 1
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"{value_col} by {label_col}"
                    }
                },
                "scales": {
                    "y": {
                        "beginAtZero": True
                    }
                }
            }
        }

    return {"error": "Unable to determine appropriate chart type for this data"}


def _generate_colors(count):
    """Generate a list of colors for chart data"""
    base_colors = [
        "#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6",
        "#06B6D4", "#F97316", "#84CC16", "#EC4899", "#6366F1"
    ]
    colors = []
    for i in range(count):
        colors.append(base_colors[i % len(base_colors)])
    return colors
