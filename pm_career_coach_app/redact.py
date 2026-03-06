import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a privacy specialist. Redact all PII from coaching notes while preserving 100% of coaching value.

Apply these replacements:
- Student names → [STUDENT]
- Coach/advisor names → [COACH]
- Any other person's names → [PERSON]
- Schools attended → [UNIVERSITY]
- Previous employers → [PREVIOUS COMPANY]
- Target companies → [TARGET COMPANY]
- Job titles that could identify someone → [ROLE]
- Identifying locations → [LOCATION]
- Graduation years → [GRAD YEAR]
- Anything else identifying → [REDACTED]
- URLs containing names → [REDACTED URL]

Keep generic resource URLs intact.
Flag anything uncertain with [REVIEW NEEDED].
Return only the redacted text, no commentary."""


def chunk_text(text: str, chunk_size: int = 10000, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks by word count."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


def redact_chunk(chunk: str, index: int, total: int) -> str:
    """Send a single chunk to Claude for redaction."""
    print(f"  Processing chunk {index + 1}/{total} ({len(chunk.split())} words)...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8096,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Redact this chunk of coaching notes:\n\n{chunk}"
        }]
    )
    return response.content[0].text.strip()


def main():
    # Load raw notes
    input_file = "coaching_notes_raw.txt"
    output_file = "coaching_notes_redacted.txt"

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Run the PDF extraction first.")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        raw_text = f.read()

    total_words = len(raw_text.split())
    print(f"Loaded {total_words:,} words from {input_file}")

    # Chunk the text
    chunks = chunk_text(raw_text, chunk_size=10000, overlap=200)
    print(f"Split into {len(chunks)} chunks. Starting redaction...\n")

    # Redact each chunk
    redacted_chunks = []
    failed_chunks = []

    for i, chunk in enumerate(chunks):
        try:
            redacted = redact_chunk(chunk, i, len(chunks))
            redacted_chunks.append(redacted)
        except Exception as e:
            print(f"  !! Chunk {i + 1} failed: {e}. Saving raw chunk with warning.")
            failed_chunks.append(i + 1)
            redacted_chunks.append(f"[REDACTION FAILED FOR THIS SECTION - MANUAL REVIEW REQUIRED]\n\n{chunk}")

    # Join and save
    final_text = "\n\n".join(redacted_chunks)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_text)

    print(f"\nDone.")
    print(f"  Input:  {total_words:,} words")
    print(f"  Output: {len(final_text.split()):,} words")
    print(f"  Chunks: {len(chunks)} processed, {len(failed_chunks)} failed")
    if failed_chunks:
        print(f"  Failed chunks (need manual review): {failed_chunks}")
    print(f"  Saved to: {output_file}")

    # Quick PII scan on output
    print("\nRunning quick PII check on output...")
    common_names = ["sunny", "audrey", "bhavya", "hemanth", "matthew", "alicia", "shaurya", "meisam"]
    found = [name for name in common_names if name.lower() in final_text.lower()]
    if found:
        print(f"  [REVIEW NEEDED] Possible names still present: {found}")
    else:
        print(f"  No obvious names detected in output.")


if __name__ == "__main__":
    main()