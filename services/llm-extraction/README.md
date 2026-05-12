# LLM Extraction Serivce

## Start up
```bash
cd LLMExtraction
cp .env-example .env
```
Enter OpenAI API key ``OPENAI_API_KEY=sk-proj-DQ....`` in .env

```bash
docker build -t llm-extraction .
docker run -p 8000:8000 --env-file .env llm-extraction
```
Open ``http:localhost8000/docs`` to see routes