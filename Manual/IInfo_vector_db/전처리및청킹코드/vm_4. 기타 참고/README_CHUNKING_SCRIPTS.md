# VM_V4 Chunking Scripts Documentation

This directory contains 6 Python scripts for chunking legal documents and glossaries into JSON format for vector database ingestion.

## Scripts Overview

### chunk1.py - 공동주택 분양가격의 산정 등에 관한 규칙
- **Document Type**: 국토교통부령 (Ministry Regulation)
- **Structure**: 4 chapters, 20 articles
- **Features**:
  - Calculation formulas for apartment pricing
  - Reference tracking (별표, 별지, 법률, 시행령)
  - Chapter-based organization
- **Output**: 20 chunks

### chunk2.py - 공동주택 층간소음의 범위와 기준에 관한 규칙
- **Document Type**: 국토교통부령/환경부령 (Joint regulation)
- **Structure**: Very short - 3 articles, no chapters
- **Features**:
  - Dual ministry regulation (국토부 + 환경부)
  - Simple structure without chapters
  - Noise regulation standards
- **Output**: 3 chunks

### chunk3.py - 부동산 가격공시에 관한 법률 시행규칙
- **Document Type**: 국토교통부령 (Ministry Regulation)
- **Structure**: 4 chapters, 32 articles
- **Features**:
  - Extensive form references (별지 제○호서식)
  - Price disclosure procedures
  - Multiple legal references
- **Output**: 32 chunks

### chunk4.py - 부동산 가격공시에 관한 법률 시행령
- **Document Type**: 대통령령 (Presidential Decree)
- **Structure**: LARGEST - 6 chapters, 79 articles
- **Features**:
  - Most comprehensive document
  - Detailed implementation guidelines
  - Committee organization details
  - Appraisal procedures
- **Output**: 79 chunks

### chunk5.py - 부동산 가격공시에 관한 법률
- **Document Type**: 법률 (Base Law)
- **Structure**: 6 chapters, 38 articles
- **Features**:
  - Foundation law for price disclosure
  - Article type classification
  - Target classification (토지, 주택, 비주거용)
  - Legal framework definition
- **Output**: 34 chunks

### chunk6.py - 부동산_용어_95가지
- **Document Type**: Glossary (NOT a legal document)
- **Structure**: 6 sections, 95 terms
- **Features**:
  - **DIFFERENT CHUNKING STRATEGY**
  - Term-based chunking (not article-based)
  - Section categorization (매매, 임대차, 청약, etc.)
  - Term metadata (category, type, characteristics)
  - Definition length tracking
- **Output**: 92 chunks

## Common Features (Scripts 1-5: Legal Documents)

All legal document chunking scripts include:
- BOM removal for proper encoding
- Chapter/article extraction
- Metadata extraction (rule number, enforcement date)
- Reference tracking (법률, 시행령, 시행규칙, 별표, 별지)
- Proper statistics output
- Error handling for encoding issues

## Unique Feature (Script 6: Glossary)

The glossary script uses a completely different strategy:
- **No legal structure** (no 조/항/호)
- Each term definition becomes a chunk
- Extracts: term number, term name, definition
- Groups by section (매매 용어, 임대차 용어, etc.)
- Metadata includes category, abbreviation status, tax/legal/financial flags

## Output Format

All scripts generate JSON files with the following structure:

### Legal Documents (chunks 1-5)
```json
{
  "id": "article_N",
  "text": "제N조(조항명) 조항내용...",
  "metadata": {
    "rule_title": "규칙명/시행령명/법률명",
    "rule_number": "제○호",
    "enforcement_date": "YYYY. M. D.",
    "article_number": "제N조",
    "article_title": "조항명",
    "chapter": "제N장 장명",
    "law_references": [...],
    "decree_references": [...],
    ...
  }
}
```

### Glossary (chunk 6)
```json
{
  "id": "term_category_N",
  "text": "용어명: 용어정의",
  "metadata": {
    "glossary_title": "부동산 용어 95가지",
    "section": "섹션명",
    "term_number": N,
    "term_name": "용어명",
    "term_category": "카테고리",
    "document_type": "glossary",
    "is_abbreviation": true/false,
    "is_tax_related": true/false,
    "is_legal_term": true/false,
    ...
  }
}
```

## Generated Files Summary

1. **공동주택 층간소음의 범위와 기준에 관한 규칙_chunked.json**
   - Chunks: 3
   - Size: ~2.4 KB

2. **부동산 가격공시에 관한 법률 시행규칙_chunked.json**
   - Chunks: 32
   - Size: ~34.4 KB

3. **부동산 가격공시에 관한 법률 시행령_chunked.json**
   - Chunks: 79
   - Size: ~120.3 KB (LARGEST)

4. **부동산 가격공시에 관한 법률_chunked.json**
   - Chunks: 34
   - Size: ~60.0 KB

5. **부동산_용어_95가지_chunked.json**
   - Chunks: 92
   - Size: ~49.8 KB

**Total: 240 chunks across 5 files**

## Usage

Run each script individually:
```bash
python chunk1.py
python chunk2.py
python chunk3.py
python chunk4.py
python chunk5.py
python chunk6.py
```

Or run all at once:
```bash
for i in {1..6}; do python chunk$i.py; done
```

## Error Handling

All scripts include:
- FileNotFoundError handling
- Unicode encoding fallback (UTF-8 → CP949)
- Unicode output error handling for statistics
- JSON save error handling

## Statistics Output

Each script provides:
- Total article/term count
- Chapter/section distribution
- Reference statistics
- Special feature counts
- For glossary: definition length statistics

## Notes

- Scripts are designed to run in the vm_v4 directory
- Input files must be in the same directory
- Output JSON files use UTF-8 encoding with ensure_ascii=False
- All metadata is preserved in Korean for better semantic understanding
- BOM (Byte Order Mark) is removed from all input files

## Next Steps

These JSON files are ready for:
1. Vector embedding generation
2. ChromaDB ingestion
3. RAG (Retrieval Augmented Generation) implementation
4. Semantic search functionality