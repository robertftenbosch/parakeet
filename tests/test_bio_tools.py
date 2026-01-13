"""Tests for Parakeet bioinformatics tools."""

from unittest.mock import patch, MagicMock

import pytest

from parakeet.core.bio_tools import (
    kegg_tool,
    pdb_tool,
    uniprot_tool,
    ncbi_tool,
    ontology_tool,
    _build_pdb_search_query,
)


class TestKeggTool:
    """Tests for kegg_tool."""

    def test_find_operation(self):
        """Tests KEGG find operation."""
        mock_response = MagicMock()
        mock_response.text = "path:map00910\tNitrogen metabolism\npath:map01310\tNitrogen cycle"
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = kegg_tool("nitrogen", operation="find", database="pathway")

        assert result["count"] == 2
        assert result["results"][0]["id"] == "path:map00910"

    def test_get_operation(self):
        """Tests KEGG get operation."""
        mock_response = MagicMock()
        mock_response.text = "ENTRY map00910\nNAME Nitrogen metabolism"
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = kegg_tool("map00910", operation="get")

        assert "content" in result
        assert "ENTRY" in result["content"]

    def test_list_operation(self):
        """Tests KEGG list operation."""
        mock_response = MagicMock()
        mock_response.text = "ec:1.1.1.1\talcohol dehydrogenase"
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = kegg_tool("*", operation="list", database="enzyme")

        assert result["count"] == 1

    def test_unknown_operation(self):
        """Returns error for unknown operation."""
        result = kegg_tool("test", operation="invalid")
        assert "error" in result

    def test_api_error(self):
        """Handles API errors gracefully."""
        with patch("requests.get", side_effect=Exception("Connection error")):
            result = kegg_tool("test", operation="find")
        assert "error" in result


class TestPdbTool:
    """Tests for pdb_tool."""

    def test_get_operation(self):
        """Tests PDB get operation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "struct": {"title": "Test Structure"},
            "exptl": [{"method": "X-RAY DIFFRACTION"}],
            "rcsb_entry_info": {"resolution_combined": [2.0]},
            "rcsb_accession_info": {"deposit_date": "2020-01-01"},
            "struct_keywords": {"pdbx_keywords": "PROTEIN"}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = pdb_tool("1ABC", operation="get")

        assert result["pdb_id"] == "1ABC"
        assert result["title"] == "Test Structure"

    def test_search_operation(self):
        """Tests PDB search operation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result_set": [
                {"identifier": "1ABC", "score": 1.0},
                {"identifier": "2DEF", "score": 0.9}
            ],
            "total_count": 2
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response):
            result = pdb_tool("nitrogenase", operation="search")

        assert result["total_count"] == 2
        assert len(result["results"]) == 2

    def test_unknown_operation(self):
        """Returns error for unknown operation."""
        result = pdb_tool("test", operation="invalid")
        assert "error" in result


class TestBuildPdbSearchQuery:
    """Tests for _build_pdb_search_query helper."""

    def test_keyword_search(self):
        """Builds keyword search query."""
        query = _build_pdb_search_query("nitrogenase", "keyword")
        assert query["query"]["service"] == "full_text"
        assert query["query"]["parameters"]["value"] == "nitrogenase"

    def test_organism_search(self):
        """Builds organism search query."""
        query = _build_pdb_search_query("Azotobacter", "organism")
        assert query["query"]["service"] == "text"
        assert "organism" in query["query"]["parameters"]["attribute"]

    def test_enzyme_search(self):
        """Builds enzyme search query."""
        query = _build_pdb_search_query("1.18.6.1", "enzyme")
        assert query["query"]["service"] == "text"
        assert "ec_lineage" in query["query"]["parameters"]["attribute"]


class TestUniprotTool:
    """Tests for uniprot_tool."""

    def test_get_operation(self):
        """Tests UniProt get operation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "primaryAccession": "P12345",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Test Protein"}}
            },
            "organism": {"scientificName": "Test organism"},
            "sequence": {"value": "MKTLV", "length": 5},
            "comments": [],
            "uniProtKBCrossReferences": []
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = uniprot_tool("P12345", operation="get")

        assert result["accession"] == "P12345"
        assert result["name"] == "Test Protein"

    def test_search_operation(self):
        """Tests UniProt search operation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "primaryAccession": "P12345",
                    "proteinDescription": {
                        "recommendedName": {"fullName": {"value": "Test"}}
                    },
                    "organism": {"scientificName": "Test org"},
                    "sequence": {"length": 100}
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = uniprot_tool("nitrogenase", operation="search")

        assert result["count"] == 1
        assert result["results"][0]["accession"] == "P12345"

    def test_fasta_operation(self):
        """Tests UniProt FASTA operation."""
        mock_response = MagicMock()
        mock_response.text = ">sp|P12345|TEST\nMKTLV"
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = uniprot_tool("P12345", operation="fasta")

        assert "fasta" in result
        assert ">sp|P12345" in result["fasta"]


class TestNcbiTool:
    """Tests for ncbi_tool."""

    def test_search_operation(self):
        """Tests NCBI search operation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "esearchresult": {
                "idlist": ["123", "456"],
                "count": "2"
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = ncbi_tool("nitrogenase", database="protein", operation="search")

        assert result["count"] == 2
        assert result["ids"] == ["123", "456"]

    def test_summary_operation(self):
        """Tests NCBI summary operation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "uids": ["123"],
                "123": {
                    "title": "Test protein",
                    "organism": "Test org",
                    "accessionversion": "ABC123"
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = ncbi_tool("123", database="protein", operation="summary")

        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Test protein"

    def test_fetch_operation(self):
        """Tests NCBI fetch operation."""
        mock_response = MagicMock()
        mock_response.text = ">ABC123\nMKTLV"
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = ncbi_tool("123", database="protein", operation="fetch")

        assert result["format"] == "fasta"
        assert "MKTLV" in result["content"]


class TestOntologyTool:
    """Tests for ontology_tool."""

    def test_search_operation(self):
        """Tests ontology search operation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "docs": [
                    {
                        "obo_id": "GO:0009399",
                        "label": "nitrogen fixation",
                        "description": ["The process"],
                        "ontology_name": "go"
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = ontology_tool("nitrogen fixation", ontology="go", operation="search")

        assert result["count"] == 1
        assert result["results"][0]["id"] == "GO:0009399"

    def test_get_operation(self):
        """Tests ontology get operation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "_embedded": {
                "terms": [{
                    "obo_id": "GO:0009399",
                    "label": "nitrogen fixation",
                    "description": ["The process"],
                    "synonyms": ["N2 fixation"],
                    "ontology_name": "go"
                }]
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = ontology_tool("GO:0009399", ontology="go", operation="get")

        assert result["id"] == "GO:0009399"
        assert result["label"] == "nitrogen fixation"

    def test_unknown_operation(self):
        """Returns error for unknown operation."""
        result = ontology_tool("test", operation="invalid")
        assert "error" in result
