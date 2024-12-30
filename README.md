# LLM-Identify-Document

This project uses a Large Language Model (LLM), specifically Google Gemini, to identify and extract information from documents within images.  It's built using FastAPI for the API and leverages Gemini's vision capabilities to process image data.

## Functionality

The API accepts an image file as input and performs the following steps:

1. **Document Identification:** The image is sent to the Gemini LLM along with a prompt instructing it to identify the types of documents present (e.g., ID card, invoice, utility bill).  A predefined list of document categories is provided to the model.

2. **Information Extraction:**  Based on the identified document types, a second prompt instructs Gemini to extract key information from each document.  This might include name, address, dates, account numbers, etc., depending on the document type.

3. **JSON Output:** The extracted information is returned as a JSON array.  Each object in the array represents a document, with its type and extracted data as key-value pairs.

## Usage

To use the API, send a POST request to `/process_image/` with the image file in the request body. The response will be a JSON object containing a success message and the extracted data.

**Example Request (using curl):**

```bash
curl -X POST -F "file=@path/to/your/image.png" http://localhost:8000/process_image/
```

**Example Response:**

```json
{
  "message": "Image processed successfully.",
  "response": [
    {
      "tipo_documento": "Carteira de Identidade",
      "nome": "João da Silva",
      "cpf": "12345678900"
    },
    {
      "tipo_documento": "Fatura de Energia",
      "nome_cliente": "Maria Souza",
      "endereco": "Rua A, 123",
      "cidade": "São Paulo",
      "estado": "SP"
    }
  ]
}
```

## Setup

1. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variable:** Set the `GEMINI_API_KEY` environment variable with your Google Gemini API key.

3. **Run the API:**

   ```bash
   uvicorn main:app --reload
   ```

## Code Structure

* `main.py`: Contains the FastAPI application, prompt definitions, and functions for interacting with the Gemini API.
* `pyproject.toml`: Specifies project metadata and dependencies.

## Error Handling

The code includes error handling for potential issues like JSON decoding errors and network problems.  Error messages are printed to the console and the raw Gemini response is printed for debugging purposes.

## Future Improvements

* More robust error handling and user feedback.
* Support for different image formats.
* Improved prompt engineering for better accuracy.
* Integration with a database for storing processed data.
