# chunking -> vectorise -> rank

def chunk(page_details):
    page_content = page_details["content"].split()
    separator = ["."]
    chunk_size = 300
    max_chunk_size = 500
    chunks = []
    i = 0
    while i < len(page_content):
        start = i
        end = i + chunk_size
        if end > len(page_content):
            end = len(page_content) - 1

        else:
            while end < len(page_content) and not page_content[end].endswith(tuple(separator)) and end - start + 1 < max_chunk_size:
                end += 1 

        current_chunk = page_content[start:end + 1]
        if(len(current_chunk) > 20):
            chunks.append({**page_details, "content": " ".join(current_chunk), "id": page_details["content_hash"]+"_"+str(len(chunks)+1), "size": len(current_chunk)})

        i = end + 1

    return chunks