# Data Pipeline

Flexible data pipeline for collecting, processing, and indexing knowledge for Kaso AI Assistant.

## Overview

```
[URLs/Markdown Files] → [Scraper/Direct] → [Cleaner] → [Chunker] → [Indexer] → [ChromaDB]
```

## Data Sources

The pipeline supports two types of data sources:

| Source Type | Description | Example |
|-------------|-------------|---------|
| **URLs** | Web pages scraped automatically | `kaso_data_sources.csv` |
| **Markdown Files** | Research reports, documentation, summaries | `kaso_research_report.md` |

### Markdown Files (Recommended for Custom Content)

You can add any `.md` file containing research, summaries, or documentation about Kaso:

```bash
# Add a research report or summary
python -m data_pipeline.run_pipeline --markdown path/to/your_summary.md

# Add multiple markdown files
python -m data_pipeline.chunker --markdown report1.md
python -m data_pipeline.chunker --markdown report2.md
python -m data_pipeline.indexer
```

**Best practices for markdown files:**
- Use clear headings (`#`, `##`, `###`) for better chunking
- Include relevant keywords in Arabic and English
- Keep paragraphs focused on single topics
- Add context about sources when relevant

## ✅ Incremental Updates

The pipeline is designed to support **incremental updates**:

| Component | Behavior |
|-----------|----------|
| **Scraper** | Only fetches new URLs (tracks status in `scrape_status.json`) |
| **Cleaner** | Processes all raw files (fast operation) |
| **Chunker** | Regenerates chunks (can be filtered by source) |
| **Indexer** | **Adds new documents** to existing collection (no reset needed) |

### Adding New Data (Incremental)

```bash
# 1. Add new URL to data sources
echo "29,https://new-source.com/article" >> data/kaso_data_sources.csv

# 2. Run pipeline - only new URLs will be fetched
python -m data_pipeline.run_pipeline
```

### Full Rebuild

```bash
# Reset everything and rebuild from scratch
python -m data_pipeline.run_pipeline --reset
```

## Pipeline Steps

### 1. Scraper (`scraper.py`)

Fetches content from URLs defined in `kaso_data_sources.csv`.

```bash
python -m data_pipeline.scraper [--force]
```

| Option | Description |
|--------|-------------|
| `--force` | Re-scrape all URLs (ignore cache) |

**Incremental:** Tracks scraped URLs in `scrape_status.json`. New URLs are automatically detected and fetched.

### 2. Cleaner (`cleaner.py`)

Cleans and normalizes scraped content.

```bash
python -m data_pipeline.cleaner
```

- Removes HTML artifacts
- Normalizes whitespace
- Removes common boilerplate

### 3. Chunker (`chunker.py`)

Splits documents into chunks for embedding.

```bash
python -m data_pipeline.chunker [--markdown FILE] [--chunk-size N] [--overlap N]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--markdown` | Process a specific markdown file | - |
| `--chunk-size` | Characters per chunk | 500 |
| `--overlap` | Overlap between chunks | 50 |

**Example:** Process the research report:
```bash
python -m data_pipeline.chunker --markdown "../kaso_research_report.md"
```

### 4. Indexer (`indexer.py`)

Indexes chunks into ChromaDB vector database.

```bash
python -m data_pipeline.indexer [--reset]
```

| Option | Description |
|--------|-------------|
| `--reset` | Clear collection before indexing |

**Incremental:** By default, new chunks are **added** to existing collection. Use `--reset` only for full rebuild.

## Data Files

| File | Description |
|------|-------------|
| `data/kaso_data_sources.csv` | URL sources (add new rows for new sources) |
| `data/raw/*.json` | Raw scraped content |
| `data/processed/*.json` | Cleaned content |
| `data/chunks/*.json` | Document chunks |
| `data/chroma_db/` | ChromaDB vector database |
| `data/scrape_status.json` | Scraping status tracker |

## Source CSV Format

```csv
المصادر,الروابط
1,https://example.com/article1
2,https://example.com/article2
```

Or:

```csv
id,url
1,https://example.com/article1
2,https://example.com/article2
```

## Full Pipeline Runner

```bash
# Run all steps (incremental by default)
python -m data_pipeline.run_pipeline

# Run with options
python -m data_pipeline.run_pipeline [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--no-scrape` | Skip URL scraping |
| `--no-clean` | Skip cleaning |
| `--no-chunk` | Skip chunking |
| `--no-index` | Skip indexing |
| `--markdown FILE` | Include a markdown file |
| `--reset` | Reset ChromaDB before indexing |

## Examples

### Add a New Article

```bash
# 1. Add URL
echo "30,https://example.com/new-article" >> data/kaso_data_sources.csv

# 2. Run pipeline
python -m data_pipeline.run_pipeline
```

### Update Research Report

```bash
# Re-process only the markdown file
python -m data_pipeline.chunker --markdown "../kaso_research_report.md"
python -m data_pipeline.indexer
```

### Complete Reset

```bash
# Clear everything and rebuild
python -m data_pipeline.run_pipeline --reset
```
