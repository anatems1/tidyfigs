# Methods — RAG framework for pavement inspection reports

We propose a retrieval-augmented generation (RAG) framework for answering engineering questions over
pavement inspection reports. In an offline indexing stage, scanned reports are converted to text through
OCR, segmented into semantically coherent chunks, and encoded with a 3,072-dimensional embedding model;
the resulting vectors are stored in a vector database together with metadata such as route, milepost,
and inspection year. At query time, a practitioner's question is embedded with the same model, and the
top-k most similar chunks are retrieved and re-ranked by a cross-encoder. The re-ranked context is
inserted into a structured prompt, and a large language model generates an answer with citations to the
source chunks. Finally, pavement engineers review each answer for factual accuracy and usefulness; their
ratings are logged and used to tune the chunk size, the value of k, and the prompt template, closing the
loop between system output and expert judgment.
