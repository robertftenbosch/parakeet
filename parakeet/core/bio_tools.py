"""Bioinformatics tools for Parakeet - KEGG, PDB, UniProt, NCBI, Ontologies."""

import re
from typing import Any, Optional
from urllib.parse import quote

import requests

from ..ui import console

# API base URLs
KEGG_API = "https://rest.kegg.jp"
PDB_API = "https://data.rcsb.org/rest/v1"
PDB_SEARCH_API = "https://search.rcsb.org/rcsbsearch/v2/query"
UNIPROT_API = "https://rest.uniprot.org"
NCBI_API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
EBI_OLS_API = "https://www.ebi.ac.uk/ols4/api"

# Request timeout
TIMEOUT = 30


def kegg_tool(
    query: str,
    operation: str = "find",
    database: str = "pathway"
) -> dict[str, Any]:
    """
    Query the KEGG database for metabolic pathways, enzymes, reactions, and compounds.

    Args:
        query: Search term or KEGG ID (e.g., 'nitrogen', 'map00910', 'K02588')
        operation: Type of operation - 'find' (search), 'get' (retrieve by ID), 'list' (list entries), 'link' (cross-references)
        database: KEGG database - 'pathway', 'enzyme', 'reaction', 'compound', 'genes', 'organism'

    Returns:
        Dict with results from KEGG API
    """
    console.print(f"  [dim]KEGG {operation}:[/] {database}/{query}")

    try:
        if operation == "find":
            # Search KEGG database
            url = f"{KEGG_API}/find/{database}/{quote(query)}"
            response = requests.get(url, timeout=TIMEOUT)

        elif operation == "get":
            # Get entry by ID
            url = f"{KEGG_API}/get/{quote(query)}"
            response = requests.get(url, timeout=TIMEOUT)

        elif operation == "list":
            # List entries in database
            url = f"{KEGG_API}/list/{database}"
            if query and query != "*":
                url = f"{KEGG_API}/list/{database}/{quote(query)}"
            response = requests.get(url, timeout=TIMEOUT)

        elif operation == "link":
            # Get cross-references
            # query should be source database, database is target
            url = f"{KEGG_API}/link/{database}/{quote(query)}"
            response = requests.get(url, timeout=TIMEOUT)

        elif operation == "conv":
            # Convert IDs between databases
            url = f"{KEGG_API}/conv/{database}/{quote(query)}"
            response = requests.get(url, timeout=TIMEOUT)

        else:
            return {"error": f"Unknown operation: {operation}. Use 'find', 'get', 'list', 'link', or 'conv'"}

        response.raise_for_status()

        # Parse KEGG response (tab-separated or flat file format)
        content = response.text
        if operation in ("find", "list", "link", "conv"):
            # Parse tab-separated results
            results = []
            for line in content.strip().split("\n"):
                if line and "\t" in line:
                    parts = line.split("\t")
                    results.append({"id": parts[0], "description": parts[1] if len(parts) > 1 else ""})
                elif line:
                    results.append({"id": line, "description": ""})
            return {"results": results, "count": len(results)}
        else:
            # Return raw content for 'get' operation (flat file)
            return {"content": content, "format": "kegg_flat"}

    except requests.exceptions.RequestException as e:
        return {"error": f"KEGG API error: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}


def pdb_tool(
    query: str,
    operation: str = "search",
    search_type: str = "keyword"
) -> dict[str, Any]:
    """
    Query the RCSB Protein Data Bank for protein structures.

    Args:
        query: Search term, PDB ID, or sequence
        operation: 'search' (find structures), 'get' (retrieve by PDB ID), 'sequence' (search by sequence)
        search_type: For search - 'keyword', 'organism', 'enzyme', 'gene'

    Returns:
        Dict with PDB results
    """
    console.print(f"  [dim]PDB {operation}:[/] {query[:50]}...")

    try:
        if operation == "get":
            # Get structure by PDB ID
            pdb_id = query.upper().strip()
            url = f"{PDB_API}/core/entry/{pdb_id}"
            response = requests.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()

            return {
                "pdb_id": pdb_id,
                "title": data.get("struct", {}).get("title", ""),
                "organism": data.get("rcsb_entity_source_organism", [{}])[0].get("scientific_name", "") if data.get("rcsb_entity_source_organism") else "",
                "resolution": data.get("rcsb_entry_info", {}).get("resolution_combined", [None])[0],
                "method": data.get("exptl", [{}])[0].get("method", ""),
                "deposit_date": data.get("rcsb_accession_info", {}).get("deposit_date", ""),
                "keywords": data.get("struct_keywords", {}).get("pdbx_keywords", ""),
            }

        elif operation == "search":
            # Search PDB using RCSB Search API
            search_query = _build_pdb_search_query(query, search_type)
            response = requests.post(
                PDB_SEARCH_API,
                json=search_query,
                headers={"Content-Type": "application/json"},
                timeout=TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for hit in data.get("result_set", [])[:20]:  # Limit to 20 results
                results.append({
                    "pdb_id": hit.get("identifier", ""),
                    "score": hit.get("score", 0)
                })

            return {
                "results": results,
                "total_count": data.get("total_count", 0),
                "query": query,
                "search_type": search_type
            }

        elif operation == "sequence":
            # Sequence search using mmseqs2 via RCSB
            search_query = {
                "query": {
                    "type": "terminal",
                    "service": "sequence",
                    "parameters": {
                        "evalue_cutoff": 0.1,
                        "identity_cutoff": 0.3,
                        "sequence_type": "protein",
                        "value": query
                    }
                },
                "return_type": "entry",
                "request_options": {
                    "results_content_type": ["experimental"],
                    "sort": [{"sort_by": "score", "direction": "desc"}],
                    "pager": {"start": 0, "rows": 20}
                }
            }
            response = requests.post(
                PDB_SEARCH_API,
                json=search_query,
                headers={"Content-Type": "application/json"},
                timeout=TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for hit in data.get("result_set", []):
                results.append({
                    "pdb_id": hit.get("identifier", ""),
                    "score": hit.get("score", 0)
                })

            return {
                "results": results,
                "total_count": data.get("total_count", 0)
            }

        else:
            return {"error": f"Unknown operation: {operation}. Use 'search', 'get', or 'sequence'"}

    except requests.exceptions.RequestException as e:
        return {"error": f"PDB API error: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}


def _build_pdb_search_query(query: str, search_type: str) -> dict:
    """Build RCSB PDB search query based on search type."""
    if search_type == "keyword":
        return {
            "query": {
                "type": "terminal",
                "service": "full_text",
                "parameters": {"value": query}
            },
            "return_type": "entry",
            "request_options": {
                "results_content_type": ["experimental"],
                "sort": [{"sort_by": "score", "direction": "desc"}],
                "pager": {"start": 0, "rows": 20}
            }
        }
    elif search_type == "organism":
        return {
            "query": {
                "type": "terminal",
                "service": "text",
                "parameters": {
                    "attribute": "rcsb_entity_source_organism.scientific_name",
                    "operator": "contains_words",
                    "value": query
                }
            },
            "return_type": "entry",
            "request_options": {
                "results_content_type": ["experimental"],
                "pager": {"start": 0, "rows": 20}
            }
        }
    elif search_type == "enzyme":
        return {
            "query": {
                "type": "terminal",
                "service": "text",
                "parameters": {
                    "attribute": "rcsb_polymer_entity.rcsb_ec_lineage.id",
                    "operator": "exact_match",
                    "value": query
                }
            },
            "return_type": "entry",
            "request_options": {
                "results_content_type": ["experimental"],
                "pager": {"start": 0, "rows": 20}
            }
        }
    else:  # gene or default
        return {
            "query": {
                "type": "terminal",
                "service": "full_text",
                "parameters": {"value": query}
            },
            "return_type": "entry",
            "request_options": {
                "results_content_type": ["experimental"],
                "pager": {"start": 0, "rows": 20}
            }
        }


def uniprot_tool(
    query: str,
    operation: str = "search",
    database: str = "uniprotkb",
    format: str = "json"
) -> dict[str, Any]:
    """
    Query the UniProt database for protein information.

    Args:
        query: Search term or UniProt accession (e.g., 'nitrogenase', 'P00346')
        operation: 'search' (find proteins), 'get' (retrieve by accession)
        database: 'uniprotkb', 'uniref', 'uniparc'
        format: Response format - 'json', 'fasta'

    Returns:
        Dict with protein information
    """
    console.print(f"  [dim]UniProt {operation}:[/] {query[:50]}...")

    try:
        if operation == "get":
            # Get protein by accession
            url = f"{UNIPROT_API}/uniprotkb/{query}.json"
            response = requests.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()

            return {
                "accession": data.get("primaryAccession", ""),
                "name": data.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", ""),
                "organism": data.get("organism", {}).get("scientificName", ""),
                "sequence": data.get("sequence", {}).get("value", ""),
                "sequence_length": data.get("sequence", {}).get("length", 0),
                "function": _extract_uniprot_function(data),
                "go_terms": _extract_uniprot_go(data),
                "ec_numbers": _extract_uniprot_ec(data),
                "cross_references": _extract_uniprot_xrefs(data)
            }

        elif operation == "search":
            # Search UniProt
            url = f"{UNIPROT_API}/uniprotkb/search"
            params = {
                "query": query,
                "format": "json",
                "size": 20
            }
            response = requests.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()

            results = []
            for entry in data.get("results", []):
                results.append({
                    "accession": entry.get("primaryAccession", ""),
                    "name": entry.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", ""),
                    "organism": entry.get("organism", {}).get("scientificName", ""),
                    "length": entry.get("sequence", {}).get("length", 0)
                })

            return {
                "results": results,
                "count": len(results)
            }

        elif operation == "fasta":
            # Get FASTA sequence
            url = f"{UNIPROT_API}/uniprotkb/{query}.fasta"
            response = requests.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            return {"fasta": response.text}

        else:
            return {"error": f"Unknown operation: {operation}. Use 'search', 'get', or 'fasta'"}

    except requests.exceptions.RequestException as e:
        return {"error": f"UniProt API error: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}


def _extract_uniprot_function(data: dict) -> str:
    """Extract function description from UniProt data."""
    comments = data.get("comments", [])
    for comment in comments:
        if comment.get("commentType") == "FUNCTION":
            texts = comment.get("texts", [])
            if texts:
                return texts[0].get("value", "")
    return ""


def _extract_uniprot_go(data: dict) -> list[dict]:
    """Extract GO terms from UniProt data."""
    go_terms = []
    xrefs = data.get("uniProtKBCrossReferences", [])
    for xref in xrefs:
        if xref.get("database") == "GO":
            go_terms.append({
                "id": xref.get("id", ""),
                "term": xref.get("properties", [{}])[0].get("value", "") if xref.get("properties") else ""
            })
    return go_terms[:10]  # Limit to 10


def _extract_uniprot_ec(data: dict) -> list[str]:
    """Extract EC numbers from UniProt data."""
    ec_numbers = []
    protein_desc = data.get("proteinDescription", {})
    rec_name = protein_desc.get("recommendedName", {})
    ec_list = rec_name.get("ecNumbers", [])
    for ec in ec_list:
        ec_numbers.append(ec.get("value", ""))
    return ec_numbers


def _extract_uniprot_xrefs(data: dict) -> dict:
    """Extract key cross-references from UniProt data."""
    xrefs = {}
    for xref in data.get("uniProtKBCrossReferences", []):
        db = xref.get("database", "")
        if db in ("PDB", "KEGG", "Pfam", "InterPro"):
            if db not in xrefs:
                xrefs[db] = []
            xrefs[db].append(xref.get("id", ""))
    return xrefs


def ncbi_tool(
    query: str,
    database: str = "protein",
    operation: str = "search",
    retmax: int = 20
) -> dict[str, Any]:
    """
    Query NCBI databases via Entrez E-utilities.

    Args:
        query: Search term or ID
        database: NCBI database - 'protein', 'nucleotide', 'gene', 'taxonomy', 'pubmed'
        operation: 'search' (find entries), 'fetch' (retrieve by ID), 'summary' (get summaries)
        retmax: Maximum number of results to return

    Returns:
        Dict with NCBI results
    """
    console.print(f"  [dim]NCBI {operation}:[/] {database}/{query[:50]}...")

    try:
        if operation == "search":
            # Search NCBI database
            url = f"{NCBI_API}/esearch.fcgi"
            params = {
                "db": database,
                "term": query,
                "retmax": retmax,
                "retmode": "json"
            }
            response = requests.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()

            result = data.get("esearchresult", {})
            ids = result.get("idlist", [])

            return {
                "ids": ids,
                "count": int(result.get("count", 0)),
                "database": database,
                "query": query
            }

        elif operation == "summary":
            # Get summaries for IDs
            url = f"{NCBI_API}/esummary.fcgi"
            params = {
                "db": database,
                "id": query,  # Comma-separated IDs
                "retmode": "json"
            }
            response = requests.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()

            results = []
            result_data = data.get("result", {})
            for uid in result_data.get("uids", []):
                entry = result_data.get(uid, {})
                results.append({
                    "id": uid,
                    "title": entry.get("title", ""),
                    "organism": entry.get("organism", ""),
                    "accession": entry.get("accessionversion", entry.get("caption", ""))
                })

            return {"results": results}

        elif operation == "fetch":
            # Fetch full record
            url = f"{NCBI_API}/efetch.fcgi"
            params = {
                "db": database,
                "id": query,
                "rettype": "fasta" if database in ("protein", "nucleotide") else "xml",
                "retmode": "text"
            }
            response = requests.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()

            return {
                "content": response.text,
                "format": "fasta" if database in ("protein", "nucleotide") else "xml",
                "database": database
            }

        else:
            return {"error": f"Unknown operation: {operation}. Use 'search', 'summary', or 'fetch'"}

    except requests.exceptions.RequestException as e:
        return {"error": f"NCBI API error: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}


def ontology_tool(
    query: str,
    ontology: str = "go",
    operation: str = "search"
) -> dict[str, Any]:
    """
    Query biological ontologies via EBI OLS.

    Args:
        query: Search term or ontology ID (e.g., 'nitrogen fixation', 'GO:0009399')
        ontology: Ontology to query - 'go' (Gene Ontology), 'chebi' (Chemical Entities), 'eco' (Evidence), 'ncbitaxon'
        operation: 'search' (find terms), 'get' (retrieve term by ID), 'children' (get child terms)

    Returns:
        Dict with ontology terms
    """
    console.print(f"  [dim]Ontology {operation}:[/] {ontology}/{query[:50]}...")

    try:
        if operation == "search":
            # Search ontology
            url = f"{EBI_OLS_API}/search"
            params = {
                "q": query,
                "ontology": ontology,
                "rows": 20
            }
            response = requests.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()

            results = []
            for doc in data.get("response", {}).get("docs", []):
                results.append({
                    "id": doc.get("obo_id", doc.get("short_form", "")),
                    "label": doc.get("label", ""),
                    "description": doc.get("description", [""])[0] if doc.get("description") else "",
                    "ontology": doc.get("ontology_name", "")
                })

            return {
                "results": results,
                "count": len(results)
            }

        elif operation == "get":
            # Get term by ID - need to encode the ID properly
            term_id = query.replace(":", "_")
            url = f"{EBI_OLS_API}/ontologies/{ontology}/terms"
            params = {"obo_id": query}
            response = requests.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()

            terms = data.get("_embedded", {}).get("terms", [])
            if terms:
                term = terms[0]
                return {
                    "id": term.get("obo_id", ""),
                    "label": term.get("label", ""),
                    "description": term.get("description", [""])[0] if term.get("description") else "",
                    "synonyms": term.get("synonyms", []),
                    "ontology": term.get("ontology_name", "")
                }
            return {"error": "Term not found"}

        elif operation == "children":
            # Get child terms
            term_id = query.replace(":", "_")
            url = f"{EBI_OLS_API}/ontologies/{ontology}/terms/{quote(quote(query, safe=''))}/children"
            response = requests.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()

            results = []
            for term in data.get("_embedded", {}).get("terms", []):
                results.append({
                    "id": term.get("obo_id", ""),
                    "label": term.get("label", "")
                })

            return {"results": results, "count": len(results)}

        else:
            return {"error": f"Unknown operation: {operation}. Use 'search', 'get', or 'children'"}

    except requests.exceptions.RequestException as e:
        return {"error": f"Ontology API error: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}


def blast_tool(
    sequence: str,
    program: str = "blastp",
    database: str = "nr",
    max_hits: int = 10
) -> dict[str, Any]:
    """
    Run BLAST sequence search via NCBI.

    Note: This submits a BLAST job and waits for results. Can take 30-60 seconds.

    Args:
        sequence: Protein or nucleotide sequence (FASTA or raw)
        program: BLAST program - 'blastp' (protein), 'blastn' (nucleotide), 'blastx', 'tblastn'
        database: Target database - 'nr' (non-redundant), 'swissprot', 'pdb', 'refseq_protein'
        max_hits: Maximum number of hits to return

    Returns:
        Dict with BLAST results
    """
    console.print(f"  [dim]BLAST {program}:[/] {database} ({len(sequence)} chars)")
    console.print("  [dim]Note: BLAST searches can take 30-60 seconds...[/]")

    # Clean sequence
    if not sequence.startswith(">"):
        sequence = f">query\n{sequence}"

    try:
        # Submit BLAST job
        put_url = "https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi"
        put_params = {
            "CMD": "Put",
            "PROGRAM": program,
            "DATABASE": database,
            "QUERY": sequence,
            "FORMAT_TYPE": "JSON2",
            "HITLIST_SIZE": max_hits
        }

        response = requests.post(put_url, data=put_params, timeout=TIMEOUT)
        response.raise_for_status()

        # Extract RID (Request ID)
        rid_match = re.search(r"RID = (\w+)", response.text)
        if not rid_match:
            return {"error": "Failed to submit BLAST job"}

        rid = rid_match.group(1)
        console.print(f"  [dim]BLAST job submitted:[/] {rid}")

        # Poll for results
        import time
        get_url = "https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi"

        for _ in range(60):  # Max 60 attempts (2 minutes)
            time.sleep(3)

            check_params = {
                "CMD": "Get",
                "FORMAT_OBJECT": "SearchInfo",
                "RID": rid
            }
            check_response = requests.get(get_url, params=check_params, timeout=TIMEOUT)

            if "Status=READY" in check_response.text:
                break
            elif "Status=FAILED" in check_response.text:
                return {"error": "BLAST search failed"}
            elif "Status=UNKNOWN" in check_response.text:
                return {"error": "BLAST job expired or not found"}

        # Get results
        result_params = {
            "CMD": "Get",
            "FORMAT_TYPE": "JSON2",
            "RID": rid
        }
        result_response = requests.get(get_url, params=result_params, timeout=TIMEOUT)
        result_response.raise_for_status()

        # Parse JSON results
        data = result_response.json()
        results = data.get("BlastOutput2", [{}])[0].get("report", {}).get("results", {}).get("search", {})

        hits = []
        for hit in results.get("hits", [])[:max_hits]:
            desc = hit.get("description", [{}])[0]
            hsps = hit.get("hsps", [{}])[0]
            hits.append({
                "accession": desc.get("accession", ""),
                "title": desc.get("title", ""),
                "score": hsps.get("bit_score", 0),
                "evalue": hsps.get("evalue", 0),
                "identity": hsps.get("identity", 0),
                "align_len": hsps.get("align_len", 0)
            })

        return {
            "program": program,
            "database": database,
            "hits": hits,
            "rid": rid
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"BLAST API error: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}
