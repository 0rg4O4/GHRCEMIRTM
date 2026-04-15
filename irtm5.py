from collections import defaultdict
import re

# Documents: ID -> content
docs = {
    1: "Information retrieval systems are useful",
    2: "Retrieval models are used in search systems",
    3: "Information systems manage data"
}

# Build inverted index
inverted_index = defaultdict(set)

for doc_id, text in docs.items():
    # Tokenize: lowercase, split words, remove punctuation
    words = re.findall(r'\b\w+\b', text.lower())
    for word in words:
        inverted_index[word].add(doc_id)

# Convert sets to sorted lists for clean output
inverted_index = {term: sorted(list(docs)) for term, docs in sorted(inverted_index.items())}

# Display
print("Inverted Index (term -> document IDs):\n")
for term, doc_ids in inverted_index.items():
    print(f"  {term:12} -> {doc_ids}")

# Query example
query = "information retrieval"
query_terms = re.findall(r'\b\w+\b', query.lower())

if query_terms:
    result = set(inverted_index.get(query_terms[0], []))
    for term in query_terms[1:]:
        result &= set(inverted_index.get(term, []))
    
    print(f"\nQuery '{query}':")
    print(f"  Relevant documents: {sorted(result)}")