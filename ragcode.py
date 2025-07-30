

from langchain_community.document_loaders import CSVLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA
from fastapi import FastAPI
from pydantic import BaseModel

import os
from dotenv import load_dotenv
import getpass
load_dotenv()
if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter Google API Key: ")

print("Setting up RAG system...")

CSV_PATH = "C:/Users/Seshagiri/Desktop/Handson/mcp-server-demo/iris.csv"
loader = CSVLoader(file_path=CSV_PATH)
documents = loader.load()

# Split documents
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
docs = text_splitter.split_documents(documents)

print("Creating embeddings...")
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = FAISS.from_documents(docs, embedding_model)

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.1)
qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever, return_source_documents=True)

print(" Ready! Ask your questions (type 'quit' to exit)\n")

app=FastAPI()

class QueryRequest(BaseModel):
    question:str

@app.post("/ask")
def ask_question(request:QueryRequest):
    """Receives a question, processes it through the RAG chain, 
    and returns the answer and source documents."""
    response = qa_chain.invoke(request.question)
    answer = response.get("result")
    source_documents=response.get("source_documents",[])
    
    clean_sources = [
        {"content": doc.page_content, "metadata": doc.metadata} for doc in source_documents
    ]
    
    return {
        "answer": answer,
        "source_documents": clean_sources
    }

