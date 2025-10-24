import React, { useEffect, useState, useCallback } from "react";
import { Chatbot } from "../types";
import { X, Database, Brain, Plus, Check, FileText, BookOpen, ArrowLeft, ArrowRight } from "lucide-react";
import {
  configureChatbotDatabase,
  createChatbot,
  createTemplate,
  getTemplates,
  setLLMSettings,
  getChatbotSchema,
  updateKnowledgeBaseSettings,
  previewGlobalTemplate,

} from "../services/api";
import api from "../services/api";
import { useToaster } from "../Toaster/Toaster";
import Loader from "./Loader";
import MultiDatabaseConfig from "./MultiDatabaseConfig";
import SemanticSchemaEditor from "./SemanticSchemaEditor";


interface DatabaseConnection {
  id: string;
  name: string;
  type: 'PostgreSQL' | 'SQLite' | 'BigQuery' | 'MySQL' | 'MSSQL';
  host?: string;
  port?: number;
  database?: string;
  username?: string;
  password?: string;
  projectId?: string;
  datasetId?: string;
  credentialsJson?: string;
  driver?: string;
  isConnected?: boolean;
  error?: string;
  schemaName?: string;
  availableSchemas?: string[];
  selectedTables?: string[];
}

interface ChatbotCreatorProps {
  onChatbotCreate: (chatbot: Chatbot) => void;
  onClose: () => void;
  onPromptReady?: (chatbotId: string, prompt: string) => void;
}

const ChatbotCreator: React.FC<ChatbotCreatorProps> = ({
  onChatbotCreate,
  onClose,
  onPromptReady,
}) => {
  const [formData, setFormData] = useState({
    name: "",
    aiModel: "",
    temperature: 0.7,
    template: "",
    tempName: "",
    desc: "",
    tempContent: "",
    industry: "",
    vertical: "",
    domain: "",
  });

  // Multi-database configuration state
  const [databaseConnections, setDatabaseConnections] = useState<DatabaseConnection[]>([]);
  const [databaseErrors, setDatabaseErrors] = useState<Record<string, string>>({});
  const [hasSelectedTables, setHasSelectedTables] = useState(false);
  // const [testingConnection, setTestingConnection] = useState<string | null>(null);
  const [isStepValid, setIsStepValid] = useState(true);
  const { showToast } = useToaster();
  // const[enable,setEnable]=useState(true)
  const [isTemp, setTemplate] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);

  // Validate step 3 when database connections change
  useEffect(() => {
    if (currentStep === 3) {
      validateStep(3);
    }
  }, [databaseConnections, currentStep]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [templates, setTemplates] = useState<any[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");
  const[isLoader,setLoader] = useState(false)
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false)
  const [isConfiguringDatabase, setIsConfiguringDatabase] = useState(false)
  const [includeSchema, setIncludeSchema] = useState(false);
  const [schemaPreview, setSchemaPreview] = useState<string>("");
  const [showSchemaPreview, setShowSchemaPreview] = useState(false);
  const [showTemplatePreview, setShowTemplatePreview] = useState(false);
  const [templatePreview, setTemplatePreview] = useState<string>("");
  const [finalPromptPreview, setFinalPromptPreview] = useState<string>("");
  const [chatbotId, setChatbotId] = useState<string>("");
  const [selected, setSelected] = useState<"create" | "select" | "default" | null>(null);
  const [showFinalPromptPreview, setShowFinalPromptPreview] = useState(false);
  const [finalPromptContent, setFinalPromptContent] = useState<string>("");
  // Add state for uploaded file at the top of the component
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  // Add state for password visibility
  // const [showPassword, setShowPassword] = useState(false);
  const [isLoadingSchema, setIsLoadingSchema] = useState(false);
  const [schemaLoaded, setSchemaLoaded] = useState(false);

  const allowedLLMs = ["COHERE", "CLAUDE", "GEMINI", "OPENAI", "AZURE"];

  // Knowledge base hierarchy
  const knowledgeBaseHierarchy = {
    "Healthcare & Lifesciences (HLS)": {
      "Pharmaceutical": [
        "Drug Discovery & Pre-Clinical",
        "Clinical Development", 
        "Manufacturing & Supply (CMC)",
        "Regulatory Affairs & Pharmacovigilance",
        "Commercials & Market Access"
      ],
      "Medical Devices and Diagnostics": [
        "Product Development",
        "Manufacturing & Quality",
        "Regulatory & Clinical Affairs", 
        "Service, Maintenance & Connectivity"
      ],
      "Providers & Care Delivery": [
        "Acute & Specialty Care",
        "Ambulatory & Primary Care",
        "Extended & Home Care",
        "Revenue Cycle & Operations"
      ]
    },
    "Banking, Finance, Securities & Insurance": {
      "Retail Banking": [
        "Customer On-Boarding & KYC",
        "Deposits & Savings Accounts",
        "Lending — Personal Loans & Mortgages", 
        "Cards — Issuing & Acquiring",
        "Digital & Mobile Channels"
      ],
      "Commercial & Corporate Banking": [
        "Working-Capital Finance",
        "Trade & Supply-Chain Finance",
        "Treasury & Cash-Management",
        "Commercial Lending & Syndications"
      ],
      "Investment Banking & Capital Markets": [
        "M&A Advisory",
        "Equity & Debt Capital Markets",
        "Sales & Trading (Equities, FICC)",
        "Prime Brokerage & Custody",
        "Structured Finance & Securitization"
      ]
    }
  };

  // Get available options based on current selections
  const getAvailableVerticals = (selectedIndustry: string) => {
    if (!selectedIndustry) return [];
    return Object.keys(knowledgeBaseHierarchy[selectedIndustry as keyof typeof knowledgeBaseHierarchy] || {});
  };

  const getAvailableDomains = (selectedIndustry: string, selectedVertical: string) => {
    if (!selectedIndustry || !selectedVertical) return [];
    const industryData = knowledgeBaseHierarchy[selectedIndustry as keyof typeof knowledgeBaseHierarchy];
    return industryData?.[selectedVertical as keyof typeof industryData] || [];
  };

  // Get all industries for the dropdown
  // const industries = Object.keys(knowledgeBaseHierarchy);

  useEffect(() => {
    // Only validate steps 1-5 automatically, step 6 validation should be triggered by user actions
    if (currentStep < 6) {
      validateStep(currentStep);
    }
  }, [currentStep]);


  // Initialize step 6 validation state when reaching step 6
  useEffect(() => {
    if (currentStep === 6) {
      // Set step 6 as valid initially, validation will be triggered by user actions
      setIsStepValid(true);
      setErrors({});
    }
  }, [currentStep]);

  const validateStep = (step: number, showErrors = false) => {
    const newErrors: Record<string, string> = {};

    if (step === 1) {
      if (!formData.name.trim()) newErrors.name = "Chatbot name is required";
    } else if (step === 2) {
      if (!formData.aiModel) newErrors.aiModel = "AI model is required";
      else if (!allowedLLMs.includes(formData.aiModel)) newErrors.aiModel = "Selected AI model is not supported.";
    } else if (step === 3) {
      // Validate database connection and table selection
      if (databaseConnections.length === 0) {
        newErrors.databaseConnections = "At least one database connection is required";
      } else {
        const connection = databaseConnections[0]; // Only validate the first connection
        
        // Check if the first connection is connected
        if (!connection.isConnected) {
          newErrors.databaseConnections = "First database connection must be tested and connected";
        }
        
        // Check if tables are selected
        if (!hasSelectedTables) {
          newErrors.selectedTables = "Please select at least one table before proceeding";
        }
      }
    } else if (step === 4) {
      // Semantic Schema Editor - always valid (user can proceed without making changes)
      // No validation needed as this is an optional editing step
    } else if (step === 5) {
      if (!formData.industry) {
        newErrors.industry = "Industry is required";
      }
      if (!formData.vertical) {
        newErrors.vertical = "Vertical is required";
      }
      if (!formData.domain) {
        newErrors.domain = "Domain is required";
      }
    } else if (step === 6) {
      if (!selected) {
        newErrors.selected = "Please select a template option";
      }
      // Only validate template fields if 'create' is selected
      if (selected === "create") {
        if (!formData.tempName.trim()) {
          newErrors.tempName = "Template name is required";
        }
        if (!formData.desc.trim()) {
          newErrors.desc = "Template description is required";
        }
        if (!formData.tempContent.trim()) {
          newErrors.tempContent = "Template content is required";
        }
      } else if (selected === "select") {
        if (!selectedTemplateId) {
          newErrors.selectedTemplateId = "Please select a template";
        }
      }
      // If 'default' is selected, do not require template fields
    }

    const isValid = Object.keys(newErrors).length === 0;
    if (showErrors) {
      setErrors(newErrors);
      setDatabaseErrors(newErrors);
    }
    setIsStepValid(isValid);
    return isValid;
  };

  const handleNext = async () => {
    if (validateStep(currentStep, true)) {
      try {
        if (currentStep === 1) {
          // Create chatbot on first step with temperature
          const chatbotResponse = await createChatbot(formData.name, formData.temperature);
          if (!chatbotResponse?.data?.chatbot?.chatbot_id) {
            throw new Error("Chatbot creation failed: No chatbot ID returned");
          }
          const chatbotId = chatbotResponse.data?.chatbot.chatbot_id;
          setChatbotId(chatbotId);
        } else if (currentStep === 2) {
          // Configure LLM on second step with temperature
          // Check if chatbot is already configured to avoid duplicate LLM configuration
          try {
            // First check the chatbot status
            const chatbotInfo = await api.get(`/api/chatbots/${chatbotId}`);
            console.log('🔍 Chatbot Info Response:', chatbotInfo.data);
            const chatbotStatus = chatbotInfo.data?.status;
            console.log('🔍 Chatbot Status:', chatbotStatus);
            
            // Only configure LLM if chatbot is in the right status
            if (chatbotStatus === 'created' || chatbotStatus === 'db_configured') {
              await setLLMSettings(chatbotId, formData.aiModel, formData.temperature);
            } else {
              console.log(`Chatbot status is ${chatbotStatus}, skipping LLM configuration...`);
              // Show a user-friendly message that LLM is already configured
              showToast(`LLM is already configured for this chatbot (Status: ${chatbotStatus || 'unknown'})`, 'success');
            }
          } catch (error: any) {
            // If the error is about chatbot status, skip LLM configuration
            if (error.response?.data?.error?.includes("Chatbot must be in 'created' or 'db_configured' status")) {
              console.log("LLM already configured, skipping...");
            } else {
              throw error;
            }
          }
        } else if (currentStep === 3) {
          // Configure only the first database connection for now
          if (databaseConnections.length > 0) {
            setIsConfiguringDatabase(true);
            try {
              const connection = databaseConnections[0];
              // Log the selected tables for debugging
              console.log('Selected tables before sending:', connection.selectedTables);
              
              const dbConfig = {
                db_type: connection.type.toLowerCase(),
                db_name: connection.database || connection.name,
                selected_tables: connection.selectedTables || [], // Add selected tables here
                schema_name: connection.schemaName || undefined,
                ...(connection.type === "PostgreSQL" && {
                  username: connection.username,
                  password: connection.password,
                  host: connection.host,
                  port: connection.port || 5432, // Ensure port has a default value
                }),
                ...(connection.type === "MySQL" && {
                  username: connection.username,
                  password: connection.password,
                  host: connection.host,
                  port: connection.port || 3306,
                  schema_name: connection.schemaName || undefined,
                }),
                ...(connection.type === "MSSQL" && {
                  username: connection.username,
                  password: connection.password,
                  host: connection.host,
                  port: connection.port || 1433,
                  driver: connection.driver || 'ODBC Driver 18 for SQL Server',
                  schema_name: connection.schemaName || undefined,
                }),
                ...(connection.type === "BigQuery" && {
                  project_id: connection.projectId,
                  dataset_id: connection.datasetId,
                  credentials_json: connection.credentialsJson,
                  schema_name: connection.schemaName || undefined,
                }),
                ...(connection.type === "SQLite" && {
                  db_name: connection.database,
                })
              };
              // Log the final config for debugging
              console.log('Sending database config:', dbConfig);
              await configureChatbotDatabase(chatbotId, dbConfig);
            } finally {
              setIsConfiguringDatabase(false);
            }
          }
        } else if (currentStep === 4) {
          // Semantic Schema Editor - no action needed, just proceed
          // The schema is automatically saved when user clicks "Save Changes" in the component
        } else if (currentStep === 5) {
          // Configure knowledge base settings
          const knowledgeBaseData = {
            industry: formData.industry,
            vertical: formData.vertical,
            domain: formData.domain,
            knowledge_base_file: uploadedFile ? uploadedFile.name : undefined,
          };
          await updateKnowledgeBaseSettings(chatbotId, knowledgeBaseData);
          // Get templates after knowledge base configuration
          getAllTemplate();
        }
        
        setCurrentStep(currentStep + 1);
        setErrors({});
      } catch (error: any) {
        let errorMessage = "Failed to proceed: ";
        if (error.response?.data?.error) {
          errorMessage += error.response.data.error;
        } else if (error.message) {
          errorMessage += error.message;
        } else {
          errorMessage += "Unknown error occurred";
        }
        showToast(errorMessage, "error");
      }
    }
  };

  const handlePrevious = () => {
    setCurrentStep(currentStep - 1);
    setErrors({});
  };

  const handleSubmit = async () => {
    if (!validateStep(5, true)) return;
    setLoader(true);
    try {
      if (selected === "create") {
        // Create custom template
        const payload = {
          name: formData.tempName,
          description: formData.desc,
          content: formData.tempContent,
          include_schema: includeSchema,
        };
        await createTemplate(chatbotId, payload);
      } else if (selected === "select") {
        // Use selected existing template
        const payload = {
          template_id: parseInt(selectedTemplateId),
          include_schema: includeSchema,
        };
        await createTemplate(chatbotId, payload);
      } else if (selected === "default") {
        // Use default template - pass default values
        const payload = {
          name: "default",
          description: "about the target DB",
          content: formData.tempContent,
        };
        await createTemplate(chatbotId, payload);
      }
      
      // Get the created chatbot details to pass to the callback
      const createdChatbot: Chatbot = {
        chatbot_id: chatbotId,
        name: formData.name,
        type: (databaseConnections[0]?.type === 'PostgreSQL' || databaseConnections[0]?.type === 'BigQuery' || databaseConnections[0]?.type === 'SQLite') 
          ? databaseConnections[0].type 
          : 'PostgreSQL', // Use first connection type as primary, fallback to PostgreSQL
        host: databaseConnections[0]?.host || '',
        port: databaseConnections[0]?.port || 0,
        database: databaseConnections[0]?.database || '',
        llm_name: formData.aiModel,
        temperature: formData.temperature,
        status: 'template_configured',
        created_at: new Date().toISOString(),
        db_url: '',
        template_name: ''
      };
      
      showToast("Chatbot Created successfully", "success");
      onChatbotCreate(createdChatbot);
      onClose();
    } catch (error: any) {
      let errorMessage = "Failed to create chatbot: ";
      if (error.response?.data?.error) {
        errorMessage += error.response.data.error;
      } else if (error.message) {
        errorMessage += error.message;
      } else {
        errorMessage += "Unknown error occurred";
      }
      showToast(errorMessage, "error");
    } finally {
      setLoader(false);
    }
  };

  const getAllTemplate = async () => {
    setIsLoadingTemplates(true);
    try {
      const response = await getTemplates();
      const allTemplates = response.data || [];
      
      // Filter templates based on visibility rules:
      // 1. All public templates
      // 2. Private templates owned by admin (current owner)
      // 3. Shared templates that include this chatbot
      const availableTemplates = allTemplates.filter((template: any) => {
        if (template.visibility === 'public') {
          return true; // Show all public templates
        }
        if (template.visibility === 'private' && template.owner === 'admin') {
          return true; // Show private templates owned by admin
        }
        if (template.visibility === 'shared' && template.shared_with && template.shared_with.includes(chatbotId)) {
          return true; // Show shared templates that include this chatbot
        }
        return false;
      });
      
      setTemplates(availableTemplates);
      
      // Show success message if templates were found
      if (availableTemplates.length > 0) {
        showToast(`Found ${availableTemplates.length} available template(s)`, 'success');
      }
    } catch (error) {
      // Templates might not exist yet, that's okay
      console.error('Failed to fetch templates:', error);
      setTemplates([]);
      showToast('Failed to load templates', 'error');
    } finally {
      setIsLoadingTemplates(false);
    }
  };

  const loadSchema = async () => {
    if (!chatbotId) {
      showToast("Please configure database first", "error");
      return false;
    }
    
    if (schemaLoaded && schemaPreview) {
      return true; // Schema already loaded
    }
    
    setIsLoadingSchema(true);
    try {
      console.log("Loading schema for chatbot:", chatbotId);
      const response = await getChatbotSchema(chatbotId);
      console.log("Schema response:", response);
      
      if (response.data) {
        // Handle semantic schema response
        let schemaText = "";
        if (response.data.schema_summary) {
          // Raw schema format
          schemaText = response.data.schema_summary;
        } else if (response.data.tables) {
          // Enhanced semantic schema format - create a summary
          schemaText = `Enhanced Database Schema (with AI Selection Metadata)\n`;
          schemaText += `Database Type: ${response.data.database_type || 'Unknown'}\n`;
          schemaText += `Total Tables: ${Object.keys(response.data.tables).length}\n\n`;
          
          for (const [tableName, tableData] of Object.entries(response.data.tables)) {
            const table = tableData as any;
            schemaText += `Table: ${tableName}\n`;
            if (table.business_context) {
              schemaText += `  Business Context: ${table.business_context}\n`;
            }
            
            const columns = table.columns || {};
            schemaText += `  Columns (${Object.keys(columns).length}):\n`;
            
            for (const [colName, colData] of Object.entries(columns)) {
              const col = colData as any;
              // Basic column info
              const pkMarker = (col.is_primary_key || col.pk) ? " (PK)" : "";
              const fkMarker = (col.is_foreign_key || col.fk) ? " (FK)" : "";
              const typeInfo = col.type || col.data_type || 'unknown';
              
              schemaText += `    - ${colName}: ${typeInfo}${pkMarker}${fkMarker}\n`;
              
              // Enhanced metadata
              if (col.description) {
                schemaText += `      Description: ${col.description}\n`;
              }
              if (col.business_terms && col.business_terms.length > 0) {
                schemaText += `      Business Terms: ${col.business_terms.join(', ')}\n`;
              }
              if (col.priority && col.priority !== 'medium') {
                schemaText += `      Priority: ${col.priority.toUpperCase()}\n`;
              }
              if (col.is_preferred) {
                schemaText += `      Preferred Column: Yes\n`;
              }
              if (col.use_cases && col.use_cases.length > 0) {
                schemaText += `      Use Cases: ${col.use_cases.join(', ')}\n`;
              }
              if (col.relevance_keywords && col.relevance_keywords.length > 0) {
                schemaText += `      Relevance Keywords: ${col.relevance_keywords.join(', ')}\n`;
              }
              if (col.business_context) {
                schemaText += `      Business Context: ${col.business_context}\n`;
              }
            }
            schemaText += "\n";
          }
        }
        
        if (schemaText) {
          console.log("Setting enhanced schema:", schemaText.substring(0, 100) + "...");
          setSchemaPreview(schemaText);
          setSchemaLoaded(true);
          console.log("Enhanced schema loaded successfully");
          return true;
        } else {
          console.log("No schema data in response:", response.data);
          showToast("No schema data available", "error");
          return false;
        }
      } else {
        console.log("No response data:", response);
        showToast("No schema data available", "error");
        return false;
      }
    } catch (error: any) {
      console.error("Schema loading error:", error);
      const errorMessage = error.response?.data?.error || "Failed to load schema";
      showToast(errorMessage, "error");
      return false;
    } finally {
      setIsLoadingSchema(false);
    }
  };

  const fetchSchemaPreview = async () => {
    if (schemaLoaded && schemaPreview) {
      setShowSchemaPreview(true);
      return;
    }
    
    const success = await loadSchema();
    if (success) {
      setShowSchemaPreview(true);
    }
  };

 const updateFormData = (field: string, value: any) => {
  setFormData((prev) => {
    const updatedForm = { ...prev, [field]: value };

    // Run validation with the updated form
    const newErrors: Record<string, string> = {};
    if (currentStep === 1) {
      if (!updatedForm.name.trim()) newErrors.name = "Chatbot name is required";
    } else if (currentStep === 2) {
      if (!updatedForm.aiModel) newErrors.aiModel = "AI model is required";
      else if (!allowedLLMs.includes(updatedForm.aiModel)) newErrors.aiModel = "Selected AI model is not supported.";
    } else if (currentStep === 3) {
      // Database validation is now handled by MultiDatabaseConfig component
      // and the validateStep function above
    } else if (currentStep === 4) {
      // Semantic Schema Editor - no validation needed
    } else if (currentStep === 5) {
      if (!updatedForm.industry) {
        newErrors.industry = "Industry is required";
      }
      if (!updatedForm.vertical) {
        newErrors.vertical = "Vertical is required";
      }
      if (!updatedForm.domain) {
        newErrors.domain = "Domain is required";
      }
    } else if (currentStep === 6) {
      if (!selected) {
        newErrors.selected = "Please select a template option";
      }
      if (selected === "create") {
        if (!updatedForm.tempName.trim()) {
          newErrors.tempName = "Template name is required";
        }
        if (!updatedForm.desc.trim()) {
          newErrors.desc = "Template description is required";
        }
        if (!updatedForm.tempContent.trim()) {
          newErrors.tempContent = "Template content is required";
        }
      } else if (selected === "select") {
        if (!selectedTemplateId) {
          newErrors.selectedTemplateId = "Please select a template";
        }
      }
    }
    
    const isValid = Object.keys(newErrors).length === 0;
    setIsStepValid(isValid);
    setErrors(newErrors);

    return updatedForm;
  });
};

  const handleSelect = async (type: "create" | "select" | "default") => {
    setSelected(type);
    if (type === "create") {
      setTemplate(true);
      validateStep(5, true);
    } else if (type === "select") {
      setTemplate(false);
      // Reset template selection
      setSelectedTemplateId("");
      // Don't validate immediately for select - validation will happen when template is selected
    } else {
      setTemplate(false);
      // Set default template values
      setFormData((prev) => ({
        ...prev,
        tempName: "default",
        desc: "about the target DB",
        tempContent: ""
      }));
      // Fetch schema and set as content
      if (chatbotId) {
        try {
          const response = await getChatbotSchema(chatbotId);
          setFormData((prev) => {
            const updated = {
              ...prev,
              tempContent: response.data.schema_summary || ""
            };
            // Trigger validation after schema is set
            setTimeout(() => validateStep(5, true), 0);
            return updated;
          });
        } catch (error: any) {
          const errorMessage = error.response?.data?.error || "Could not fetch schema.";
          showToast(errorMessage, "error");
          setFormData((prev) => {
            const updated = {
              ...prev,
              tempContent: "Could not fetch schema."
            };
            setTimeout(() => validateStep(5, true), 0);
            return updated;
          });
        }
      } else {
        setTimeout(() => validateStep(5, true), 0);
      }
    }
  };

  const previewTemplate = async (templateId: string) => {
    try {
      const response = await previewGlobalTemplate(parseInt(templateId), {
        chatbot_id: chatbotId,
        include_schema: includeSchema,
      });
      const data = response.data;
      setTemplatePreview(data.template.content);
      setFinalPromptPreview(data.final_prompt);
      setShowTemplatePreview(true);
    } catch (error) {
      showToast("Failed to preview template", "error");
    }
  };

  const generateFinalPromptPreview = useCallback(async () => {
    if (!chatbotId) return;
    
    try {
      let templateContent = "";
      
      if (selected === "select" && selectedTemplateId) {
        // Get selected template content
        const selectedTemplate = templates.find(t => t.id.toString() === selectedTemplateId);
        templateContent = selectedTemplate?.content || "";
      } else if (selected === "create") {
        // Use custom template content
        templateContent = formData.tempContent;
      } else if (selected === "default") {
        // Use default template content (schema)
        templateContent = formData.tempContent;
      }

      let finalPrompt = templateContent;
      
      if (includeSchema && templateContent) {
        try {
          // Use loaded schema if available
          if (schemaLoaded && schemaPreview) {
            finalPrompt = `${schemaPreview}\n\n${templateContent}`;
          } else {
            // Schema not loaded yet, show message
            finalPrompt = `[Schema will be loaded when checkbox is checked]\n\n${templateContent}`;
          }
        } catch (error: any) {
          const errorMessage = error.response?.data?.error || "Failed to fetch schema for preview";
          console.error("Failed to fetch schema for preview:", errorMessage);
        }
      }
      
      setFinalPromptContent(finalPrompt);
    } catch (error) {
      console.error("Failed to generate final prompt preview:", error);
    }
  }, [chatbotId, selected, selectedTemplateId, templates, formData.tempContent, includeSchema]);

  // Update final prompt preview when relevant values change
  useEffect(() => {
    if (selected && (selectedTemplateId || selected === "create" || selected === "default")) {
      generateFinalPromptPreview();
    }
  }, [selected, selectedTemplateId, includeSchema, formData.tempContent, chatbotId, templates]);

  // Trigger validation when selectedTemplateId changes
  useEffect(() => {
    if (currentStep === 6 && selected === "select") {
      validateStep(6, true);
    }
  }, [selectedTemplateId, currentStep, selected]);

  useEffect(() => {
    if (chatbotId && finalPromptContent && onPromptReady) {
      onPromptReady(chatbotId, finalPromptContent);
    }
  }, [chatbotId, finalPromptContent, onPromptReady]);

  return (
    <>
      {isLoader && <Loader />}
    
      <div className="min-h-screen bg-gray-50 flex flex-col pt-[70px]">
        {/* Static Header */}
        <div className="fixed top-[70px] left-0 right-0 bg-white shadow-sm border-b border-gray-200 z-10">
          <div className="max-w-6xl mx-auto px-6 py-2">
            <div className="flex items-center justify-between">
              <h1 className="text-lg font-bold text-gray-900">
                Create New Chatbot
              </h1>
              
              {/* Progress Bar */}
              <div className="flex items-center space-x-4">
                {[1, 2, 3, 4, 5, 6].map((step) => (
                  <React.Fragment key={step}>
                    <div className="flex items-center">
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold ${
                          step <= currentStep
                            ? "bg-blue-600 text-white"
                            : "bg-gray-200 text-gray-600"
                        }`}
                      >
                        {step < currentStep ? <Check className="w-4 h-4" /> : step}
                      </div>
                      <span className="ml-2 text-xs font-medium text-gray-600">
                        {step === 1 && "Basic Info"}
                        {step === 2 && "LLM Settings"}
                        {step === 3 && "Database Settings"}
                        {step === 4 && "Schema Editor"}
                        {step === 5 && "Knowledge Base Settings"}
                        {step === 6 && "Template Settings"}
                      </span>
                    </div>
                    {step < 6 && (
                      <div
                        className={`w-8 h-0.5 rounded-full ${
                          step < currentStep ? "bg-blue-600" : "bg-gray-200"
                        }`}
                      />
                    )}
                  </React.Fragment>
                ))}
              </div>
              
              <button
                onClick={onClose}
                className="w-8 h-8 flex items-center justify-center text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>



        {/* Scrollable Content Area */}
        <div className="flex-1 overflow-y-auto pt-[96px]">
          <div className="max-w-6xl mx-auto px-6 py-8 pb-24">
            {currentStep === 1 && (
              <div className="max-w-2xl mx-auto">
                <div className="text-center mb-6">
                  <h2 className="text-xl font-bold text-gray-900 mb-2">
                    Let's start with the basics
                  </h2>
                  <p className="text-gray-600">
                    Give your chatbot a name to get started
                  </p>
                </div>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Chatbot Name *
                    </label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => updateFormData("name", e.target.value)}
                      className={`w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors ${
                        errors.name ? "border-red-300 focus:ring-red-500 focus:border-red-500" : "border-gray-300"
                      }`}
                      placeholder="Enter a descriptive name for your chatbot"
                    />
                    {errors.name && (
                      <p className="text-red-500 text-sm mt-2 flex items-center">
                        <span className="mr-1">⚠️</span>
                        {errors.name}
                      </p>
                    )}
                  </div>
                  
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-start">
                      <div className="flex-shrink-0">
                        <svg className="h-5 w-5 text-blue-500" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <div className="ml-3">
                        <h3 className="text-sm font-medium text-blue-900 mb-2">
                          Naming Tips
                        </h3>
                        <div className="text-blue-800 text-sm">
                          <ul className="space-y-1">
                            <li className="flex items-start">
                              <span className="text-blue-600 mr-2">•</span>
                              <span>Use a descriptive name that reflects the chatbot's purpose</span>
                            </li>
                            <li className="flex items-start">
                              <span className="text-blue-600 mr-2">•</span>
                              <span>Keep it concise but meaningful</span>
                            </li>
                            <li className="flex items-start">
                              <span className="text-blue-600 mr-2">•</span>
                              <span>Examples: "Customer Support Bot", "Sales Assistant", "HR Helper"</span>
                            </li>
                          </ul>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: AI Model Configuration */}
            {currentStep === 2 && (
              <div className="space-y-6">
                <div className="text-center mb-6">
                  <Brain className="w-12 h-12 text-blue-500 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                    AI Model Configuration
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400">
                    Select the AI model and configure its settings
                  </p>
                </div>

                {/* AI Model Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    AI Model *
                  </label>
                  <select
                    value={formData.aiModel}
                    onChange={(e) => updateFormData("aiModel", e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  >
                    <option value="">Select AI Model</option>
                    <option value="OPENAI">OpenAI GPT-4o</option>
                    <option value="AZURE">Azure GPT-4o Mini</option>
                    <option value="COHERE">Cohere Command R+</option>
                    <option value="GEMINI">Google Gemini 1.5 Pro</option>
                    <option value="CLAUDE">Claude 3 Opus</option>
                  </select>
                  {errors.aiModel && (
                    <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                      {errors.aiModel}
                    </p>
                  )}
                </div>

                {/* Temperature Configuration */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Temperature
                  </label>
                  <div className="space-y-2">
                    <input
                      type="number"
                      min="0"
                      max="1"
                      step="0.001"
                      value={formData.temperature}
                      onChange={(e) => updateFormData("temperature", parseFloat(e.target.value) || 0)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                      placeholder="0.7"
                    />
                    <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                      <span>0.0 (Focused)</span>
                      <span>1.0 (Creative)</span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Enter precise temperature value (0.0 to 1.0). Lower values make the AI more focused and deterministic. Higher values make it more creative and diverse.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {currentStep === 3 && (
              <MultiDatabaseConfig
                connections={databaseConnections}
                onConnectionsChange={setDatabaseConnections}
                errors={databaseErrors}
                onTableSelectionChange={setHasSelectedTables}
                onTestConnection={async (connection) => {
                   try {
                     // This would call your backend API to test the connection
                     // For now, we'll simulate a test
                     const dbConfig = {
                       db_type: connection.type.toLowerCase(),
                       db_name: connection.database || connection.name,
                       ...(connection.type === "PostgreSQL" && {
                         username: connection.username,
                         password: connection.password,
                         host: connection.host,
                         port: connection.port || 5432, // Ensure port has a default value
                       }),
                       ...(connection.type === "MySQL" && {
                         username: connection.username,
                         password: connection.password,
                         host: connection.host,
                         port: connection.port || 3306,
                       }),
                       ...(connection.type === "MSSQL" && {
                         username: connection.username,
                         password: connection.password,
                         host: connection.host,
                         port: connection.port || 1433,
                         driver: connection.driver || 'ODBC Driver 18 for SQL Server',
                       }),
                       ...(connection.type === "BigQuery" && {
                         project_id: connection.projectId,
                         dataset_id: connection.datasetId,
                         credentials_json: connection.credentialsJson,
                       }),
                       ...(connection.type === "SQLite" && {
                         db_name: connection.database,
                       }),
                     };
                     
                     console.log('Testing connection with config:', dbConfig);
                     
                     // Call the real backend API to test the connection
                     const response = await api.post('/api/test-connection', dbConfig);
                     const schemas = response.data?.schemas || [];
                     const list = (schemas && schemas.length > 0) ? schemas : [];
                     return { success: !!response.data.success, schemas: list };
                   } catch (error) {
                     console.error('Connection test failed:', error);
                     return { success: false, schemas: [] };
                   }
                 }}
                onFetchTables={async (connection) => {
                   try {
                     const dbConfig = {
                       db_type: connection.type.toLowerCase(),
                       db_name: connection.database || connection.name,
                       schema_name: connection.schemaName || undefined,
                       ...(connection.type === "PostgreSQL" && {
                         username: connection.username,
                         password: connection.password,
                         host: connection.host,
                         port: connection.port || 5432,
                       }),
                       ...(connection.type === "MySQL" && {
                         username: connection.username,
                         password: connection.password,
                         host: connection.host,
                         port: connection.port || 3306,
                       }),
                       ...(connection.type === "MSSQL" && {
                         username: connection.username,
                         password: connection.password,
                         host: connection.host,
                         port: connection.port || 1433,
                         driver: connection.driver || 'ODBC Driver 18 for SQL Server',
                       }),
                     };
                     const response = await api.post('/api/test-connection', dbConfig);
                     const tables = response.data?.tables || [];
                     return { success: !!response.data.success, tables };
                   } catch (error) {
                     console.error('Fetch tables failed:', error);
                     return { success: false, tables: [], error: (error as any)?.message };
                   }
                 }}
              />
            )}

            {currentStep === 4 && (
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                  <Database className="w-5 h-5 mr-2" />
                  Schema Configuration
                </h3>
                <SemanticSchemaEditor 
                  chatbotId={chatbotId}
                  onSave={() => {
                    showToast('Schema updated successfully', 'success');
                  }}
                  onConfirm={() => {
                    showToast('Schema configured successfully', 'success');
                    setCurrentStep(currentStep + 1);
                  }}
                />
              </div>
            )}

            {currentStep === 5 && (
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                  <BookOpen className="w-5 h-5 mr-2" />
                  Knowledge Base Settings
                </h3>
                <div className="grid grid-cols-1 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Industry *
                    </label>
                    <select
                      value={formData.industry}
                      onChange={(e) => {
                        updateFormData("industry", e.target.value);
                        // Reset dependent fields when industry changes
                        updateFormData("vertical", "");
                        updateFormData("domain", "");
                      }}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                    >
                      <option value="">Select Industry</option>
                      {Object.keys(knowledgeBaseHierarchy).map((industry) => (
                        <option key={industry} value={industry}>
                          {industry}
                        </option>
                      ))}
                    </select>
                    {errors.industry && (
                      <p className="text-red-500 text-sm mt-1">{errors.industry}</p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Vertical *
                    </label>
                    <select
                      value={formData.vertical}
                      onChange={(e) => {
                        updateFormData("vertical", e.target.value);
                        // Reset domain when vertical changes
                        updateFormData("domain", "");
                      }}
                      disabled={!formData.industry}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 disabled:cursor-not-allowed"
                    >
                      <option value="">Select Vertical</option>
                      {getAvailableVerticals(formData.industry).map((vertical) => (
                        <option key={vertical} value={vertical}>
                          {vertical}
                        </option>
                      ))}
                    </select>
                    {errors.vertical && (
                      <p className="text-red-500 text-sm mt-1">{errors.vertical}</p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Domain *
                    </label>
                    <select
                      value={formData.domain}
                      onChange={(e) => updateFormData("domain", e.target.value)}
                      disabled={!formData.vertical}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 disabled:cursor-not-allowed"
                    >
                      <option value="">Select Domain</option>
                      {getAvailableDomains(formData.industry, formData.vertical).map((domain) => (
                        <option key={domain} value={domain}>
                          {domain}
                        </option>
                      ))}
                    </select>
                    {errors.domain && (
                      <p className="text-red-500 text-sm mt-1">{errors.domain}</p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Knowledge Base File (Optional)
                    </label>
                    {!uploadedFile ? (
                      <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-6 text-center">
                        <input
                          type="file"
                          id="file-upload"
                          className="hidden"
                          accept=".pdf,.docx,.txt,.md,.csv"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) {
                              setUploadedFile(file);
                            }
                          }}
                        />
                        <label
                          htmlFor="file-upload"
                          className="cursor-pointer flex flex-col items-center"
                        >
                          <FileText className="w-8 h-8 text-gray-400 mb-2" />
                          <span className="text-sm text-gray-600 dark:text-gray-400">
                            Click to upload or drag and drop
                          </span>
                          <span className="text-xs text-gray-500 mt-1">
                            PDF, DOCX, TXT, MD, CSV (max 10MB)
                          </span>
                        </label>
                      </div>
                    ) : (
                      <div className="border border-gray-300 dark:border-gray-600 rounded-lg p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-3">
                            <FileText className="w-5 h-5 text-blue-500" />
                            <div>
                              <p className="text-sm font-medium text-gray-900 dark:text-white">
                                {uploadedFile.name}
                              </p>
                              <p className="text-xs text-gray-500">
                                {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                              </p>
                            </div>
                          </div>
                          <button
                            onClick={() => setUploadedFile(null)}
                            className="text-sm text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
                          >
                            Remove
                          </button>
                        </div>
                      </div>
                    )}
                    <p className="text-xs text-gray-500 mt-2">
                      Upload a file to provide additional context for your chatbot's knowledge base.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {currentStep === 6 && (
              <div className="space-y-6">
                {/* Template Selection Cards - Large and Centered */}
                {!selected && (
                  <div className="flex flex-col items-center justify-center min-h-[400px]">
                    <div className="text-center mb-8">
                      <h2 className="text-2xl font-bold text-gray-900 mb-2">
                        Choose Your Template
                      </h2>
                      <p className="text-gray-600">
                        Select how'd like to configure your chatbot template
                      </p>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl w-full">
                      <button
                        onClick={() => handleSelect("create")}
                        className="group p-8 border-2 border-gray-200 rounded-xl text-center transition-all duration-200 hover:border-blue-300 hover:shadow-lg hover:scale-105 bg-white"
                      >
                        <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4 group-hover:bg-blue-200 transition-colors">
                          <Plus className="w-8 h-8 text-blue-600" />
                        </div>
                        <h3 className="text-xl font-semibold text-gray-900 mb-2">
                          Create New
                        </h3>
                        <p className="text-gray-600 leading-relaxed">
                          Start from scratch and build a completely custom template tailored to your specific needs
                        </p>
                      </button>
                      
                      <button
                        onClick={() => handleSelect("select")}
                        className="group p-8 border-2 border-gray-200 rounded-xl text-center transition-all duration-200 hover:border-green-300 hover:shadow-lg hover:scale-105 bg-white"
                      >
                        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4 group-hover:bg-green-200 transition-colors">
                          <FileText className="w-8 h-8 text-green-600" />
                        </div>
                        <h3 className="text-xl font-semibold text-gray-900 mb-2">
                          Select Existing
                        </h3>
                        <p className="text-gray-600 leading-relaxed">
                          Choose from our library of pre-built templates designed for common use cases
                        </p>
                      </button>
                      
                      <button
                        onClick={() => handleSelect("default")}
                        className="group p-8 border-2 border-gray-200 rounded-xl text-center transition-all duration-200 hover:border-purple-300 hover:shadow-lg hover:scale-105 bg-white"
                      >
                        <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4 group-hover:bg-purple-200 transition-colors">
                          <Database className="w-8 h-8 text-purple-600" />
                        </div>
                        <h3 className="text-xl font-semibold text-gray-900 mb-2">
                          Use Default
                        </h3>
                        <p className="text-gray-600 leading-relaxed">
                          Get started quickly with our recommended default settings
                        </p>
                      </button>
                    </div>
                  </div>
                )}
                
                {/* Selected Template Options - Compact at Top */}
                {selected && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-3 gap-3">
                      <button
                        className={`rounded-md px-3 py-2 text-xs flex items-center justify-center cursor-pointer border transition-all ${
                          selected === "create"
                            ? "bg-[#6658dd] border-gray-300 text-white"
                            : "bg-white text-gray-700 border-gray-300 hover:bg-gray-100"
                        }`}
                        onClick={() => handleSelect("create")}
                      >
                        <Plus className="w-3 h-3 mr-1" />
                        Create New
                      </button>

                      <button
                        className={`rounded-md px-3 py-2 text-xs flex items-center justify-center cursor-pointer border transition-all ${
                          selected === "select"
                            ? "bg-[#6658dd] border-gray-300 text-white"
                            : "bg-white text-gray-700 border-gray-300 hover:bg-gray-100"
                        }`}
                        onClick={() => handleSelect("select")}
                      >
                        <FileText className="w-3 h-3 mr-1" />
                        Select Existing
                      </button>

                      <button
                        className={`rounded-md px-3 py-2 flex text-xs items-center justify-center cursor-pointer border transition-all ${
                          selected === "default"
                            ? "bg-[#6658dd] text-white"
                            : "bg-white text-gray-700 border-gray-300 hover:bg-gray-100"
                        }`}
                        onClick={() => handleSelect("default")}
                      >
                        <Database className="w-3 h-3 mr-1" />
                        Use Default
                      </button>
                    </div>
                  </div>
                )}

                {/* Schema Inclusion Option - Above all templates */}
                {selected && (
                  <div className="mt-4 p-4 bg-gray-50 rounded-md border border-gray-200">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={includeSchema}
                          onChange={async (e) => {
                            const checked = e.target.checked;
                            setIncludeSchema(checked);
                            
                            if (checked && !schemaLoaded) {
                              // Load schema when checkbox is checked and schema not already loaded
                              await loadSchema();
                            }
                          }}
                          className="mr-2"
                        />
                        <span className="text-sm font-medium">Include Database Schema</span>
                      </label>
                      {includeSchema && (
                        <button
                          type="button"
                          onClick={fetchSchemaPreview}
                          disabled={isLoadingSchema}
                          className={`text-sm flex items-center ${
                            isLoadingSchema 
                              ? 'text-gray-400 cursor-not-allowed' 
                              : 'text-blue-600 hover:text-blue-800'
                          }`}
                        >
                          {isLoadingSchema ? (
                            <>
                              <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full mr-1"></div>
                              Loading...
                            </>
                          ) : (
                            <>
                              <FileText className="w-4 h-4 mr-1" />
                              {schemaLoaded ? 'Preview Schema' : 'Load Schema'}
                            </>
                          )}
                        </button>
                      )}
                    </div>
                    <p className="text-xs text-gray-600 mt-1">
                      When enabled, the database schema will be automatically included at the beginning of your template
                    </p>
                    {/* Upload file button for future use */}
                    <div className="mt-4">
                      <label className="block text-sm font-medium mb-2">Upload Database Info (optional, for future use)</label>
                      <input
                        type="file"
                        accept=".txt,.csv,.json,.sql,.xlsx,.xls,.pdf,.doc,.docx"
                        onChange={e => setUploadedFile(e.target.files && e.target.files[0] ? e.target.files[0] : null)}
                        className="block w-full text-sm text-gray-700 border border-gray-300 rounded-md cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                      {uploadedFile && (
                        <div className="mt-1 text-xs text-green-700">Selected file: {uploadedFile.name}</div>
                      )}
                      <p className="text-xs text-gray-500 mt-1">You can upload any file with information about your database. This will be used for future enhancements.</p>
                    </div>
                  </div>
                )}

                {/* Template Selection */}
                {selected === "select" && (
                  <div className="mt-4">
                    <label className="block text-sm font-medium mb-2">
                      Select Template *
                    </label>
                    <div className="max-h-48 overflow-y-auto border border-gray-300 rounded-md">
                      {isLoadingTemplates ? (
                        <div className="p-6 text-center">
                          <div className="animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-2"></div>
                          <p className="text-sm text-gray-600">Loading templates...</p>
                        </div>
                      ) : templates.length > 0 ? (
                        templates.map((template) => (
                          <div
                            key={template.id}
                            className={`p-3 border-b border-gray-200 cursor-pointer hover:bg-gray-50 ${
                              selectedTemplateId === template.id.toString() ? 'bg-blue-50 border-blue-300' : ''
                            }`}
                            onClick={() => {
                              setSelectedTemplateId(template.id.toString());
                            }}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex-1">
                                <h4 className="text-sm font-medium text-gray-900">{template.name}</h4>
                                <p className="text-xs text-gray-600 mt-1">{template.description}</p>
                                <div className="flex items-center space-x-2 mt-1">
                                  <span className={`text-xs px-2 py-1 rounded ${
                                    template.visibility === 'public' ? 'bg-green-100 text-green-800' :
                                    template.visibility === 'private' ? 'bg-gray-100 text-gray-800' :
                                    'bg-blue-100 text-blue-800'
                                  }`}>
                                    {template.visibility}
                                  </span>
                                  <span className="text-xs text-gray-500">by {template.owner}</span>
                                  {template.visibility === 'shared' && (
                                    <span className="text-xs bg-orange-100 text-orange-800 px-2 py-1 rounded">
                                      Shared with you
                                    </span>
                                  )}
                                </div>
                              </div>
                              <div className="flex items-center space-x-2">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    previewTemplate(template.id.toString());
                                  }}
                                  className="text-xs text-blue-600 hover:text-blue-800 flex items-center"
                                >
                                  <FileText className="w-3 h-3 mr-1" />
                                  Preview
                                </button>
                                <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                                  selectedTemplateId === template.id.toString() 
                                    ? 'border-blue-600 bg-blue-600' 
                                    : 'border-gray-300'
                                }`}>
                                  {selectedTemplateId === template.id.toString() && (
                                    <div className="w-2 h-2 bg-white rounded-full"></div>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="p-6 text-center text-gray-500">
                          <FileText className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                          <p className="font-medium">No templates available</p>
                          <p className="text-xs mt-1">
                            You can see public templates, private templates you own, and templates shared with this chatbot.
                          </p>
                        </div>
                      )}
                    </div>
                    {errors.selectedTemplateId && (
                      <p className="text-red-500 text-sm mt-1">{errors.selectedTemplateId}</p>
                    )}
                  </div>
                )}
                {isTemp && (
                  <>
                    <div className="grid grid-cols-2 gap-4 mt-4  ">
                      <div>
                        <label className="block text-sm font-medium  mb-2">
                          Template Name *
                        </label>
                        <input
                          type="text"
                          value={formData.tempName}
                          onChange={(e) =>
                            updateFormData("tempName", e.target.value)
                          }
                          className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                            errors.tempName ? "border-red-300" : "border-gray-300"
                          }`}
                          placeholder="Templte Name"
                        />
                        {errors.tempName && (
                          <p className="text-red-500 text-sm mt-1">
                            {errors.tempName}
                          </p>
                        )}
                      </div>

                      <>
                        <div>
                          <label className="block text-sm font-medium  mb-2">
                            Template Description *
                          </label>
                          <input
                            type="text"
                            value={formData.desc}
                            placeholder="Template Description"
                            onChange={(e) =>
                              updateFormData("desc", e.target.value)
                            }
                            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                              errors.desc ? "border-red-300" : "border-gray-300"
                            }`}
                          />
                          {errors.desc && (
                            <p className="text-red-500 text-sm mt-1">
                              {errors.desc}
                            </p>
                          )}
                        </div>
                      </>
                    </div>

                    <div className="grid grid-cols-1">
                      <div>
                        <label className="block text-sm font-medium mb-2">
                          Template Content *
                        </label>
                        <textarea
                          rows={4}
                          value={formData.tempContent}
                          onChange={(e) =>
                            updateFormData("tempContent", e.target.value)
                          }
                          className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                            errors.tempContent
                              ? "border-red-300"
                              : "border-gray-300"
                          }`}
                          placeholder="Enter your template content (if schema is included above, it will be prepended automatically)..."
                        />
                        {errors.tempContent && (
                          <p className="text-red-500 text-sm mt-1">
                            {errors.tempContent}
                          </p>
                        )}
                      </div>
                    </div>
                  </>
                )}

                {/* Final Prompt Preview - Show what will be sent to LLM */}
                {selected && finalPromptContent && (
                  <div className="mt-6 p-4 bg-blue-50 rounded-md border border-blue-200">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-semibold text-blue-900">Final Prompt Preview</h3>
                      <button
                        onClick={() => setShowFinalPromptPreview(!showFinalPromptPreview)}
                        className="text-sm text-blue-600 hover:text-blue-800 flex items-center"
                      >
                        <FileText className="w-4 h-4 mr-1" />
                        {showFinalPromptPreview ? 'Hide' : 'Show'} Full Preview
                      </button>
                    </div>
                    <p className="text-xs text-blue-700 mb-2">
                      This is what will be sent to the LLM {includeSchema ? '(Schema + Template Content)' : '(Template Content only)'}
                    </p>
                    
                    {showFinalPromptPreview ? (
                      <div className="max-h-60 overflow-y-auto bg-white p-3 rounded border">
                        <pre className="text-xs whitespace-pre-wrap text-gray-800">
                          {finalPromptContent}
                        </pre>
                      </div>
                    ) : (
                      <div className="bg-white p-3 rounded border">
                        <div className="text-xs text-gray-600">
                          <div className="flex items-center space-x-2">
                            <span className="font-medium">Content Length:</span>
                            <span>{finalPromptContent.length} characters</span>
                          </div>
                          <div className="flex items-center space-x-2 mt-1">
                            <span className="font-medium">Preview:</span>
                            <span className="truncate">{finalPromptContent.substring(0, 100)}...</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Database Configuration Loader */}
        {isConfiguringDatabase && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[9999]">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
              <div className="flex flex-col items-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Configuring Database</h3>
                <p className="text-sm text-gray-600 text-center">
                  Connecting to your database and extracting schema. This may take a few moments..
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Static Footer */}
        <div className="fixed bottom-0 left-0 right-0 bg-white shadow-lg border-t border-gray-200 z-10">
          <div className="max-w-4xl mx-auto px-6 py-3">
            <div className="flex justify-between items-center">
              <button
                onClick={currentStep === 1 ? onClose : handlePrevious}
                className="px-5 py-2.5 text-gray-700 text-sm border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors flex items-center"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                {currentStep === 1 ? "Cancel" : "Previous"}
              </button>
              <button
                disabled={
                  isConfiguringDatabase ||
                  (currentStep === 6
                    ? !(isStepValid && (selected === 'create' || selected === 'select' || selected === 'default'))
                    : !isStepValid)
                }
                onClick={currentStep === 6 ? handleSubmit : handleNext}
                className={`px-6 py-2.5 rounded-lg transition-colors flex items-center text-sm font-medium ${
                  isConfiguringDatabase ||
                  (currentStep === 6
                    ? !(isStepValid && (selected === 'create' || selected === 'select' || selected === 'default'))
                    : !isStepValid)
                    ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                    : "bg-blue-600 text-white hover:bg-blue-700"
                }`}
              >
                {currentStep === 6 ? (
                  <>
                    <Plus className="w-4 h-4 mr-2" />
                    Create Chatbot
                  </>
                ) : isConfiguringDatabase ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Configuring...
                  </>
                ) : (
                  <>
                    Next
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Schema Preview Modal */}
      {showSchemaPreview && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[9999]">
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full mx-4 max-h-[80vh] flex flex-col">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold">Database Schema Preview</h3>
              <button
                onClick={() => setShowSchemaPreview(false)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="px-6 py-4 overflow-y-auto" style={{ maxHeight: '60vh' }}>
              <pre className="text-sm bg-gray-50 p-4 rounded-lg whitespace-pre-wrap">
                {schemaPreview || "No schema content available"}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* Template Preview Modal */}
      {showTemplatePreview && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[9999]">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[80vh] flex flex-col">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold">Template Preview</h3>
              <button
                onClick={() => setShowTemplatePreview(false)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="px-6 py-4 overflow-y-auto" style={{ maxHeight: '60vh' }}>
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Template Content:</h4>
                  <pre className="text-sm bg-gray-50 p-4 rounded-lg whitespace-pre-wrap border">
                    {templatePreview}
                  </pre>
                </div>
                {includeSchema && (
                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 mb-2">Final Prompt (with Schema):</h4>
                    <pre className="text-sm bg-blue-50 p-4 rounded-lg whitespace-pre-wrap border border-blue-200">
                      {finalPromptPreview}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default ChatbotCreator;
