from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from typing import List
import tempfile
import pdfplumber
import re
import pandas as pd

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def clean_text(text):
    return text.replace("_", "").replace("*", "")

def extract_cpf(line):
    cpf_pattern = r"CPF:\s*(\d{3}\.?\d{3}\.?\d{3}-?\d{2})"
    match = re.search(cpf_pattern, clean_text(line))
    return match.group(1) if match else None

def process_pdf(pdf_path):
    dados = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    lines = text.split("\n")
                    current_data = {}
                    
                    for line in lines:
                        clean_line = clean_text(line)
                        
                        if clean_line.strip().startswith("_") or not clean_line.strip():
                            continue

                        data_match = re.search(
                            r"(\d{2}/\d{2}/\d{4})\s+(.*?)\s+Bco:\s*(\d+)\s+Ag:\s*(\d+)\s+Conta:\s*(\d+)\s+R\$\s*([\d,.]+)", 
                            clean_line
                        )
                        
                        if data_match:
                            if current_data:
                                dados.append(current_data)
                            current_data = {
                                "data": data_match.group(1),
                                "nome": data_match.group(2).strip(),
                                "banco": data_match.group(3),
                                "agencia": data_match.group(4),
                                "conta": data_match.group(5),
                                "valor": data_match.group(6)
                            }
                        elif "CPF:" in clean_line:
                            cpf = extract_cpf(clean_line)
                            if cpf and current_data:
                                current_data["cpf"] = cpf
                    
                    if current_data:
                        dados.append(current_data)
                        
    except Exception as e:
        print(f"Erro ao processar {pdf_path}: {str(e)}")
    
    return dados

@app.post("/api/convert")
async def convert_pdfs(files: List[UploadFile] = File(...)):
    try:
        results = []
        with tempfile.TemporaryDirectory() as temp_dir:
            for file in files:
                temp_path = os.path.join(temp_dir, file.filename)
                with open(temp_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                data = process_pdf(temp_path)
                results.extend(data)
        
        return {"status": "success", "data": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
