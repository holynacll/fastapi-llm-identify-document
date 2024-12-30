import os
import requests
import re
import pprint
import base64
import json

from fastapi import FastAPI, UploadFile, File, HTTPException

# Configurações das APIs
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

prompt_1 = """Você é um assistante de classificação de documentos. Dado uma imagem digitalizada ou fotografia contendo um ou mais documentos, sua tarefa é descobrir a qual categoria o documento pertence na lista fornecida em <categoria-documentos>. Respeite as restrições em <obs> e retorne a resposta do conteúdo interno de <output>, como demonstrado em <exemplos>.

<categoria-documentos>
Carteira de Identidade com Foto
Solicitação de Serviço de Despesa de Receita (SSDR)  
Solicitação de Abertura de Processo  
Documento Auxiliar de Nota Fiscal Eletrônica (DANFE)  
Documento de Arrecadação Estadual (DAE)  
Comprovante de Residência  
Declaração de Residência  
Fatura de Água e/ou Esgoto
Fatura de Energia
Fatura de Serviços de Comunicação
Laudo de Vistoria  
Certificado de Registro do Veículo (CRV)  
Autorização para Transferência de Propriedade do Veículo (ATPV)  
Autorização Profissional
Procuração  
Conselho Regional de Despachante Documentalista (CRDD)
</categoria-documentos>

<obs>
Se a qualidade da imagem não permitir a identificação clara de um documento, classifique-o como “Não Identificado”.
Caso um documento identificado não se enquadre nas categorias listadas, classifique-o como “Outro documento”.
</obs>

<output>[</output>

<exemplos>
    <exemplo-1>
        Entrada: Imagem contendo um CPF e uma Carteira de Identidade
        Saída: ["CPF", "Carteira de Identidade"]
    </exemplo-1>
    <exemplo-2>
        Entrada: Imagem contendo um documento com informações de uma fatura de energia elétrica
        Saída: ["Fatura de Energia"]
    </exemplo-2>
</exemplos>
"""

prompt_2 = """Você é um assistente de extração de informações. Dada uma imagem e uma lista de tipos de documentos identificados nessa imagem, sua tarefa é extrair informações relevantes desses documentos.

**Instruções:**

*   **Entrada:** Você receberá uma imagem e uma lista de tipos de documentos identificados na imagem.
*   **Extração:** Para cada tipo de documento na lista, tente extrair as seguintes informações, se presentes:
    *   Nome
    *   Rua
    *   Bairro
    *   Cidade
    *   Estado
    *   CEP
    *   CPF
    *   CNPJ
    *   Telefone
    *   E-mail
*   **Priorização:** Priorize a extração precisa dos dados. Se a qualidade da imagem dificultar a extração de um campo específico, omita-o. Não invente informações.
*   **Formatação da Saída:** Retorne um array JSON. Para cada documento identificado, crie um objeto JSON com os seguintes campos:
    *   `tipo_documento`: O tipo do documento (ex: "Carteira de Identidade", "Fatura de Energia").
    *   Os demais campos (nome, rua, etc.) com os valores extraídos. Inclua apenas os campos para os quais você conseguiu extrair informações.
*   **Lidando com Múltiplos Documentos do Mesmo Tipo:** Se houver múltiplos documentos do mesmo tipo na imagem, crie um objeto JSON separado para cada um.
*   **Caso Nenhum Documento Seja Identificado:** Se a lista de documentos for vazia, retorne um array JSON vazio (`[]`).

**Exemplo:**

**Imagem:** [Imagem da qual os documentos foram extraídos]
**Tipos de Documentos Identificados:** ["CPF", "Carteira de Identidade", "Fatura de Energia"]

**Saída:**
```json
[
    {{
        "tipo_documento": "CPF",
        "nome": "João da Silva",
        "cpf": "123.456.789-00"
    }},
    {{
        "tipo_documento": "Carteira de Identidade",
        "nome": "João da Silva",
        "rg": "98765432-1", # Exemplo de outro campo que pode ser extraído
        "data_nascimento": "01/01/1980" # Exemplo de outro campo que pode ser extraído
    }},
    {{
        "tipo_documento": "Fatura de Energia",
        "nome_cliente": "Maria Souza", # Nome do cliente na fatura
        "endereco": "Avenida Paulista, 1000",
        "cidade": "São Paulo",
        "estado": "SP",
        "cep": "01311-920",
        "numero_instalacao": "123456789" # Exemplo de outro campo que pode ser extraído
    }}
]

**Lista de documentos a serem processados:**
{documents}
"""

prompt_steps = [prompt_1, prompt_2]


def process_gemini(content: dict):
    return content["candidates"][0]["content"]["parts"][0]["text"]


def extract_content(text: str):
    """Processa a resposta do Gemini, extraindo o JSON e tratando erros."""
    try:
        # Extrai o JSON de dentro do bloco de código (```json ... ```)
        match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
        if match:
            json_string = match.group(1)
        else:
            # Tenta analisar diretamente se não houver o bloco de código
            json_string = text

        # Remove possíveis espaços em branco extras e quebras de linha
        json_string = json_string.rstrip()

        # Verifica se a string está vazia ou contém apenas colchetes vazios
        if not json_string or json_string == "[]":
            return []  # Retorna uma lista vazia diretamente

        data = json.loads(json_string)
        return data
    except (json.JSONDecodeError, IndexError, TypeError) as e:
        print(f"Erro ao processar a resposta do Gemini: {e}")
        pprint.pprint(text)  # Imprime a resposta completa para debug
        return None  # Ou lance uma exceção, dependendo do seu caso


async def send_to_gemini(prompt: str, file_path: str):
    with open(file_path, "rb") as f:
        image_data = f.read()
    encoded_data = base64.b64encode(image_data).decode("utf-8")  # Decode to string
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": encoded_data,
                        }
                    },
                ]
            }
        ]
    }
    response = requests.post(url, json=data, headers=headers)
    return process_gemini(response.json())


async def run_prompt_chain(image_path: str):
    response_content = []
    result = []
    for key, prompt in enumerate(prompt_steps):
        if "{documents}" in prompt:
            prompt = prompt.format(documents=response_content)
        response = await send_to_gemini(prompt, image_path)
        response_content = extract_content(response)
        print(f"Prompt {key + 1}")
        print(response_content)
        print("-" * 50)
    for document in response_content:
        new_doc = {}
        for key, value in document.items():
            if value is not None:
                new_doc[key] = value
        result.append(new_doc)
    return result


app = FastAPI(
    title="Image Processing API",
    description="API for processing images using Gemini Vision.",
    version="1.0",
)


@app.post("/process_image/")
async def process_image(
    file: UploadFile = File(description="A file image to be processed"),
):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided.")
    file_name = file.filename if file.filename else "image.png"
    with open(file_name, "wb") as image:
        image.write(await file.read())
    response = await run_prompt_chain(file_name)
    return {
        "message": "Image processed successfully.",
        "response": response,
    }


@app.get("/")
def read_root():
    return {"message": "Welcome to the Image Processing API."}
