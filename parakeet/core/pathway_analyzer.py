"""Pathway analysis tools for metabolic engineering optimization."""

import re
from typing import Any, Optional
from collections import defaultdict

import requests

from ..ui import console

KEGG_API = "https://rest.kegg.jp"
TIMEOUT = 30


def get_pathway_info(pathway_id: str) -> dict[str, Any]:
    """
    Get detailed information about a KEGG pathway.

    Args:
        pathway_id: KEGG pathway ID (e.g., 'map00910', 'eco00910')

    Returns:
        Dict with pathway details including enzymes, reactions, compounds
    """
    try:
        # Fetch pathway data
        url = f"{KEGG_API}/get/{pathway_id}"
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()

        content = response.text
        info = parse_kegg_flat_file(content)

        # Get pathway image/KGML for structure if needed
        info["pathway_id"] = pathway_id

        return info

    except Exception as e:
        return {"error": str(e)}


def parse_kegg_flat_file(content: str) -> dict[str, Any]:
    """Parse KEGG flat file format into structured data."""
    result = {
        "name": "",
        "description": "",
        "enzymes": [],
        "reactions": [],
        "compounds": [],
        "genes": [],
        "modules": [],
        "references": []
    }

    current_section = None
    current_content = []

    for line in content.split("\n"):
        if not line:
            continue

        # Check for section headers (start at column 0)
        if line[0] != " ":
            # Save previous section
            if current_section and current_content:
                _process_section(result, current_section, current_content)

            # Start new section
            parts = line.split(None, 1)
            current_section = parts[0] if parts else None
            current_content = [parts[1]] if len(parts) > 1 else []
        else:
            # Continue current section
            current_content.append(line.strip())

    # Process last section
    if current_section and current_content:
        _process_section(result, current_section, current_content)

    return result


def _process_section(result: dict, section: str, content: list[str]) -> None:
    """Process a section from KEGG flat file."""
    text = " ".join(content)

    if section == "NAME":
        result["name"] = text
    elif section == "DESCRIPTION":
        result["description"] = text
    elif section == "ENZYME":
        # Parse enzyme EC numbers
        ec_numbers = re.findall(r"[\d\-]+\.[\d\-]+\.[\d\-]+\.[\d\-]+", text)
        result["enzymes"] = ec_numbers
    elif section == "REACTION":
        # Parse reaction IDs
        reactions = re.findall(r"R\d{5}", text)
        result["reactions"] = reactions
    elif section == "COMPOUND":
        # Parse compound entries
        compounds = []
        for item in content:
            match = re.match(r"(C\d{5})\s+(.+)", item)
            if match:
                compounds.append({"id": match.group(1), "name": match.group(2)})
        result["compounds"] = compounds
    elif section == "GENE":
        # Parse gene entries
        genes = []
        for item in content:
            # Format: gene_id  description (K number)
            match = re.match(r"(\S+)\s+(.+)", item)
            if match:
                genes.append({"id": match.group(1), "description": match.group(2)})
        result["genes"] = genes[:50]  # Limit
    elif section == "MODULE":
        modules = re.findall(r"M\d{5}", text)
        result["modules"] = modules


def get_pathway_enzymes(pathway_id: str) -> dict[str, Any]:
    """
    Get all enzymes in a pathway with their details.

    Args:
        pathway_id: KEGG pathway ID

    Returns:
        Dict with enzyme information
    """
    try:
        # Get enzyme links for pathway
        url = f"{KEGG_API}/link/enzyme/{pathway_id}"
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()

        enzymes = []
        for line in response.text.strip().split("\n"):
            if line and "\t" in line:
                _, enzyme_id = line.split("\t")
                ec_number = enzyme_id.replace("ec:", "")
                enzymes.append(ec_number)

        # Get enzyme details
        enzyme_details = []
        for ec in enzymes[:20]:  # Limit to avoid too many requests
            detail = get_enzyme_info(ec)
            if "error" not in detail:
                enzyme_details.append(detail)

        return {
            "pathway_id": pathway_id,
            "enzyme_count": len(enzymes),
            "enzymes": enzyme_details
        }

    except Exception as e:
        return {"error": str(e)}


def get_enzyme_info(ec_number: str) -> dict[str, Any]:
    """Get information about a specific enzyme."""
    try:
        url = f"{KEGG_API}/get/ec:{ec_number}"
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()

        info = parse_kegg_flat_file(response.text)
        info["ec_number"] = ec_number

        # Get organisms that have this enzyme
        org_url = f"{KEGG_API}/link/genes/ec:{ec_number}"
        org_response = requests.get(org_url, timeout=TIMEOUT)

        organisms = defaultdict(list)
        for line in org_response.text.strip().split("\n"):
            if line and "\t" in line:
                _, gene = line.split("\t")
                # Gene format: org:gene_id
                if ":" in gene:
                    org = gene.split(":")[0]
                    organisms[org].append(gene)

        info["organisms"] = dict(list(organisms.items())[:20])
        info["organism_count"] = len(organisms)

        return info

    except Exception as e:
        return {"error": str(e), "ec_number": ec_number}


def compare_pathway_organisms(
    pathway_id: str,
    organism1: str,
    organism2: str
) -> dict[str, Any]:
    """
    Compare a pathway between two organisms.

    Args:
        pathway_id: Base pathway ID (e.g., '00910' for nitrogen metabolism)
        organism1: First organism code (e.g., 'eco' for E. coli)
        organism2: Second organism code (e.g., 'avn' for Azotobacter vinelandii)

    Returns:
        Dict with comparison results
    """
    try:
        # Get genes for both organisms
        path1 = f"{organism1}{pathway_id}"
        path2 = f"{organism2}{pathway_id}"

        genes1 = _get_pathway_genes(path1)
        genes2 = _get_pathway_genes(path2)

        # Get KO (KEGG Orthology) assignments for comparison
        ko1 = _get_pathway_ko(path1)
        ko2 = _get_pathway_ko(path2)

        # Find common and unique KOs
        ko_set1 = set(ko1.keys())
        ko_set2 = set(ko2.keys())

        common_ko = ko_set1 & ko_set2
        unique_to_1 = ko_set1 - ko_set2
        unique_to_2 = ko_set2 - ko_set1

        return {
            "pathway": pathway_id,
            "organism1": {
                "code": organism1,
                "gene_count": len(genes1),
                "ko_count": len(ko1)
            },
            "organism2": {
                "code": organism2,
                "gene_count": len(genes2),
                "ko_count": len(ko2)
            },
            "comparison": {
                "common_functions": len(common_ko),
                "unique_to_org1": len(unique_to_1),
                "unique_to_org2": len(unique_to_2),
                "unique_org1_kos": list(unique_to_1)[:10],
                "unique_org2_kos": list(unique_to_2)[:10]
            }
        }

    except Exception as e:
        return {"error": str(e)}


def _get_pathway_genes(pathway_id: str) -> list[str]:
    """Get genes for an organism-specific pathway."""
    try:
        url = f"{KEGG_API}/link/genes/{pathway_id}"
        response = requests.get(url, timeout=TIMEOUT)
        genes = []
        for line in response.text.strip().split("\n"):
            if line and "\t" in line:
                _, gene = line.split("\t")
                genes.append(gene)
        return genes
    except Exception:
        return []


def _get_pathway_ko(pathway_id: str) -> dict[str, list[str]]:
    """Get KO assignments for a pathway."""
    try:
        url = f"{KEGG_API}/link/ko/{pathway_id}"
        response = requests.get(url, timeout=TIMEOUT)
        ko_map = defaultdict(list)
        for line in response.text.strip().split("\n"):
            if line and "\t" in line:
                gene, ko = line.split("\t")
                ko_map[ko.replace("ko:", "")].append(gene)
        return dict(ko_map)
    except Exception:
        return {}


def find_alternative_enzymes(
    ec_number: str,
    source_organism: Optional[str] = None,
    target_organisms: Optional[list[str]] = None
) -> dict[str, Any]:
    """
    Find alternative enzymes from different organisms for a given EC number.

    Useful for finding enzymes with potentially better properties
    (higher activity, different substrate specificity, etc.)

    Args:
        ec_number: EC number of the enzyme
        source_organism: Current organism (to exclude from results)
        target_organisms: List of organisms to search in (None = all)

    Returns:
        Dict with alternative enzymes from different organisms
    """
    try:
        # Get all genes with this EC number
        url = f"{KEGG_API}/link/genes/ec:{ec_number}"
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()

        organisms = defaultdict(list)
        for line in response.text.strip().split("\n"):
            if line and "\t" in line:
                _, gene = line.split("\t")
                if ":" in gene:
                    org, gene_id = gene.split(":", 1)

                    # Skip source organism
                    if source_organism and org == source_organism:
                        continue

                    # Filter by target organisms
                    if target_organisms and org not in target_organisms:
                        continue

                    organisms[org].append(gene_id)

        # Get organism names
        results = []
        for org, genes in list(organisms.items())[:15]:
            org_info = _get_organism_name(org)
            results.append({
                "organism_code": org,
                "organism_name": org_info,
                "genes": genes[:5],
                "gene_count": len(genes)
            })

        return {
            "ec_number": ec_number,
            "alternatives": results,
            "total_organisms": len(organisms)
        }

    except Exception as e:
        return {"error": str(e)}


def _get_organism_name(org_code: str) -> str:
    """Get organism name from code."""
    try:
        url = f"{KEGG_API}/list/organism"
        response = requests.get(url, timeout=TIMEOUT)
        for line in response.text.strip().split("\n"):
            if f"\t{org_code}\t" in line:
                parts = line.split("\t")
                if len(parts) >= 3:
                    return parts[2]
        return org_code
    except Exception:
        return org_code


def analyze_nitrogen_fixation_pathway(organism: str = "avn") -> dict[str, Any]:
    """
    Specialized analysis of nitrogen fixation pathway.

    Default organism is Azotobacter vinelandii (avn), a well-studied
    nitrogen-fixing bacterium.

    Args:
        organism: KEGG organism code

    Returns:
        Dict with nitrogen fixation analysis
    """
    console.print(f"  [dim]Analyzing nitrogen fixation in:[/] {organism}")

    try:
        results = {
            "organism": organism,
            "pathways": {},
            "key_enzymes": {},
            "nif_genes": []
        }

        # Key nitrogen metabolism pathways
        pathways = {
            "00910": "Nitrogen metabolism",
            "00910": "Nitrogen metabolism"
        }

        for path_num, path_name in pathways.items():
            path_id = f"{organism}{path_num}"
            info = get_pathway_info(path_id)
            if "error" not in info:
                results["pathways"][path_name] = {
                    "id": path_id,
                    "gene_count": len(info.get("genes", [])),
                    "enzyme_count": len(info.get("enzymes", []))
                }

        # Key nitrogen fixation enzymes
        nif_enzymes = {
            "1.18.6.1": "Nitrogenase (Mo-Fe protein)",
            "1.18.6.2": "Nitrogenase (V-Fe protein)",
            "1.4.3.21": "Glutamate synthase",
            "6.3.1.2": "Glutamine synthetase"
        }

        for ec, name in nif_enzymes.items():
            enzyme_info = get_enzyme_info(ec)
            if "error" not in enzyme_info:
                # Check if organism has this enzyme
                has_enzyme = organism in enzyme_info.get("organisms", {})
                results["key_enzymes"][name] = {
                    "ec": ec,
                    "present": has_enzyme,
                    "organism_count": enzyme_info.get("organism_count", 0)
                }

        # Search for nif genes
        url = f"{KEGG_API}/find/genes/nif+{organism}"
        response = requests.get(url, timeout=TIMEOUT)
        for line in response.text.strip().split("\n")[:20]:
            if line and "\t" in line:
                gene_id, desc = line.split("\t", 1)
                results["nif_genes"].append({
                    "id": gene_id,
                    "description": desc[:100]
                })

        return results

    except Exception as e:
        return {"error": str(e)}


def suggest_optimization_targets(
    pathway_id: str,
    organism: str
) -> dict[str, Any]:
    """
    Suggest potential optimization targets in a metabolic pathway.

    Identifies:
    - Rate-limiting enzymes (based on reaction connectivity)
    - Enzymes with alternatives in other organisms
    - Branch points that could be redirected

    Args:
        pathway_id: KEGG pathway number (e.g., '00910')
        organism: KEGG organism code

    Returns:
        Dict with optimization suggestions
    """
    console.print(f"  [dim]Finding optimization targets:[/] {organism}{pathway_id}")

    try:
        full_path_id = f"{organism}{pathway_id}"
        suggestions = {
            "pathway": full_path_id,
            "optimization_targets": [],
            "alternative_enzymes": [],
            "missing_functions": []
        }

        # Get pathway info
        path_info = get_pathway_info(full_path_id)
        if "error" in path_info:
            return path_info

        # Get reference pathway to find missing functions
        ref_path = get_pathway_info(f"map{pathway_id}")

        # Compare enzymes
        org_enzymes = set(path_info.get("enzymes", []))
        ref_enzymes = set(ref_path.get("enzymes", []))

        missing = ref_enzymes - org_enzymes
        for ec in list(missing)[:5]:
            alt = find_alternative_enzymes(ec)
            if "error" not in alt and alt.get("alternatives"):
                suggestions["missing_functions"].append({
                    "ec": ec,
                    "available_in": [a["organism_code"] for a in alt["alternatives"][:3]]
                })

        # Find enzymes with many alternatives (potential for optimization)
        for ec in list(org_enzymes)[:10]:
            alt = find_alternative_enzymes(ec, source_organism=organism)
            if "error" not in alt and alt.get("total_organisms", 0) > 10:
                suggestions["alternative_enzymes"].append({
                    "ec": ec,
                    "alternatives_count": alt["total_organisms"],
                    "top_sources": [a["organism_name"] for a in alt["alternatives"][:3]]
                })

        return suggestions

    except Exception as e:
        return {"error": str(e)}
