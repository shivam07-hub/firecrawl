"""Isolate LM Studio call — run directly: python3 test_llm.py"""
from openai import OpenAI
from config import LM_STUDIO_BASE_URL, LM_STUDIO_API_KEY, LM_STUDIO_MODEL
from enricher import _SYSTEM_PROMPT, _ENRICH_PROMPT

client = OpenAI(base_url=LM_STUDIO_BASE_URL, api_key=LM_STUDIO_API_KEY)

SAMPLE_JD = """
We are hiring a Senior Data Engineer to join our Data Platform team in Bengaluru.

Requirements:
- 5-8 years of experience in data engineering
- Strong proficiency in Python and SQL
- Experience with Apache Spark and Kafka
- Familiarity with AWS (S3, Redshift, Glue)
- Bachelor's degree in Computer Science or related field

Nice to have:
- Experience with dbt or Airflow
- Knowledge of streaming architectures

This is a full-time hybrid role (3 days onsite in Bengaluru).
"""

prompt = _ENRICH_PROMPT.format(title="Senior Data Engineer", jd=SAMPLE_JD)

print(f"Model:    {LM_STUDIO_MODEL}")
print(f"Base URL: {LM_STUDIO_BASE_URL}")
print(f"Prompt tokens (est): ~{len(prompt)//4}")
print("\nCalling LM Studio...")

try:
    resp = client.chat.completions.create(
        model=LM_STUDIO_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.05,
        max_tokens=300,
    )
    raw = resp.choices[0].message.content
    print(f"\nRAW RESPONSE:\n{raw}")
    print(f"\nFinish reason: {resp.choices[0].finish_reason}")
    print(f"Tokens — prompt: {resp.usage.prompt_tokens}  completion: {resp.usage.completion_tokens}")
except Exception as e:
    print(f"\nERROR: {type(e).__name__}: {e}")
