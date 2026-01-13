"""Tests for Parakeet pathway analyzer tools."""

from unittest.mock import patch, MagicMock

import pytest

from parakeet.core.tools import (
    analyze_pathway_tool,
    compare_organisms_tool,
    find_alternatives_tool,
)
from parakeet.core.pathway_analyzer import (
    parse_kegg_flat_file,
    _process_section,
    _get_pathway_genes,
    _get_pathway_ko,
    _get_organism_name,
)


class TestParseKeggFlatFile:
    """Tests for KEGG flat file parser."""

    def test_parse_name_section(self):
        """Parses NAME section correctly."""
        content = "NAME    Nitrogen metabolism"
        result = parse_kegg_flat_file(content)
        assert result["name"] == "Nitrogen metabolism"

    def test_parse_enzyme_section(self):
        """Parses ENZYME section with EC numbers."""
        content = "ENZYME  1.18.6.1  1.4.3.21  6.3.1.2"
        result = parse_kegg_flat_file(content)
        assert "1.18.6.1" in result["enzymes"]
        assert "6.3.1.2" in result["enzymes"]

    def test_parse_reaction_section(self):
        """Parses REACTION section with reaction IDs."""
        content = "REACTION R00001 R00002 R00003"
        result = parse_kegg_flat_file(content)
        assert result["reactions"] == ["R00001", "R00002", "R00003"]

    def test_parse_compound_section(self):
        """Parses COMPOUND section with compound entries."""
        content = """COMPOUND C00001  H2O; Water
            C00014  Ammonia"""
        result = parse_kegg_flat_file(content)
        assert len(result["compounds"]) == 2
        assert result["compounds"][0]["id"] == "C00001"

    def test_parse_module_section(self):
        """Parses MODULE section with module IDs."""
        content = "MODULE  M00175 M00530"
        result = parse_kegg_flat_file(content)
        assert "M00175" in result["modules"]

    def test_parse_multiline_content(self):
        """Parses multiline sections correctly."""
        content = """NAME    Nitrogen metabolism
DESCRIPTION This is a description
            that spans multiple lines
ENZYME  1.18.6.1"""
        result = parse_kegg_flat_file(content)
        assert result["name"] == "Nitrogen metabolism"
        assert "multiple lines" in result["description"]
        assert "1.18.6.1" in result["enzymes"]


class TestAnalyzePathwayTool:
    """Tests for analyze_pathway_tool."""

    def test_info_analysis(self):
        """Tests pathway info analysis."""
        mock_response = MagicMock()
        mock_response.text = "NAME    Nitrogen metabolism\nENZYME  1.18.6.1"
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = analyze_pathway_tool("map00910", analysis_type="info")

        assert result["name"] == "Nitrogen metabolism"
        assert "1.18.6.1" in result["enzymes"]

    def test_enzymes_analysis(self):
        """Tests pathway enzymes analysis."""
        mock_link_response = MagicMock()
        mock_link_response.text = "map00910\tec:1.18.6.1\nmap00910\tec:6.3.1.2"
        mock_link_response.raise_for_status = MagicMock()

        mock_enzyme_response = MagicMock()
        mock_enzyme_response.text = "NAME    Nitrogenase"
        mock_enzyme_response.raise_for_status = MagicMock()

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_link_response
            result = analyze_pathway_tool("map00910", analysis_type="enzymes")

        assert "enzyme_count" in result

    def test_nitrogen_analysis(self):
        """Tests specialized nitrogen fixation analysis."""
        mock_response = MagicMock()
        mock_response.text = "NAME    Nitrogen metabolism"
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = analyze_pathway_tool("00910", analysis_type="nitrogen")

        assert result["organism"] == "avn"

    def test_optimization_requires_organism(self):
        """Returns error when organism not provided for optimization."""
        result = analyze_pathway_tool("00910", analysis_type="optimization")
        assert "error" in result
        assert "Organism" in result["error"]

    def test_unknown_analysis_type(self):
        """Returns error for unknown analysis type."""
        result = analyze_pathway_tool("00910", analysis_type="invalid")
        assert "error" in result


class TestCompareOrganismsTool:
    """Tests for compare_organisms_tool."""

    def test_compare_two_organisms(self):
        """Tests comparing pathways between two organisms."""
        mock_response = MagicMock()
        mock_response.text = "eco00910\teco:b0001\neco00910\tko:K00001"
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = compare_organisms_tool("00910", "eco", "avn")

        assert result["pathway"] == "00910"
        assert result["organism1"]["code"] == "eco"
        assert result["organism2"]["code"] == "avn"
        assert "comparison" in result

    def test_compare_handles_api_error_gracefully(self):
        """Returns empty comparison when API fails (graceful degradation)."""
        with patch("requests.get", side_effect=Exception("Connection error")):
            result = compare_organisms_tool("00910", "eco", "avn")
        # Function returns empty results instead of error
        assert result["organism1"]["gene_count"] == 0
        assert result["organism2"]["gene_count"] == 0
        assert result["comparison"]["common_functions"] == 0


class TestFindAlternativesTool:
    """Tests for find_alternatives_tool."""

    def test_find_alternatives(self):
        """Tests finding alternative enzymes."""
        mock_response = MagicMock()
        mock_response.text = "ec:1.18.6.1\tavn:Avin0001\nec:1.18.6.1\teco:b0002"
        mock_response.raise_for_status = MagicMock()

        mock_org_response = MagicMock()
        mock_org_response.text = "genome\tavn\tAzotobacter vinelandii"

        with patch("requests.get") as mock_get:
            mock_get.side_effect = [mock_response, mock_org_response, mock_org_response]
            result = find_alternatives_tool("1.18.6.1")

        assert result["ec_number"] == "1.18.6.1"
        assert "alternatives" in result

    def test_find_alternatives_with_source_organism(self):
        """Tests excluding source organism from results."""
        mock_response = MagicMock()
        mock_response.text = "ec:1.18.6.1\tavn:Avin0001\nec:1.18.6.1\teco:b0002"
        mock_response.raise_for_status = MagicMock()

        mock_org_response = MagicMock()
        mock_org_response.text = "genome\teco\tEscherichia coli"

        with patch("requests.get") as mock_get:
            mock_get.side_effect = [mock_response, mock_org_response]
            result = find_alternatives_tool("1.18.6.1", source_organism="avn")

        assert result["ec_number"] == "1.18.6.1"

    def test_find_alternatives_with_target_organisms(self):
        """Tests filtering by target organisms."""
        mock_response = MagicMock()
        mock_response.text = "ec:1.18.6.1\tavn:Avin0001\nec:1.18.6.1\teco:b0002"
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = find_alternatives_tool("1.18.6.1", target_organisms="eco,bsu")

        assert result["ec_number"] == "1.18.6.1"

    def test_find_alternatives_handles_api_error(self):
        """Handles API errors gracefully."""
        with patch("requests.get", side_effect=Exception("Connection error")):
            result = find_alternatives_tool("1.18.6.1")
        assert "error" in result


class TestHelperFunctions:
    """Tests for internal helper functions."""

    def test_get_pathway_genes(self):
        """Tests getting genes for a pathway."""
        mock_response = MagicMock()
        mock_response.text = "eco00910\teco:b0001\neco00910\teco:b0002"

        with patch("requests.get", return_value=mock_response):
            genes = _get_pathway_genes("eco00910")

        assert len(genes) == 2
        assert "eco:b0001" in genes

    def test_get_pathway_genes_handles_error(self):
        """Returns empty list on error."""
        with patch("requests.get", side_effect=Exception("Error")):
            genes = _get_pathway_genes("eco00910")
        assert genes == []

    def test_get_pathway_ko(self):
        """Tests getting KO assignments for a pathway."""
        mock_response = MagicMock()
        mock_response.text = "eco:b0001\tko:K00001\neco:b0002\tko:K00001"

        with patch("requests.get", return_value=mock_response):
            ko_map = _get_pathway_ko("eco00910")

        assert "K00001" in ko_map
        assert len(ko_map["K00001"]) == 2

    def test_get_pathway_ko_handles_error(self):
        """Returns empty dict on error."""
        with patch("requests.get", side_effect=Exception("Error")):
            ko_map = _get_pathway_ko("eco00910")
        assert ko_map == {}

    def test_get_organism_name(self):
        """Tests getting organism name from code."""
        mock_response = MagicMock()
        mock_response.text = "genome\teco\tEscherichia coli K-12 MG1655\tProkaryotes"

        with patch("requests.get", return_value=mock_response):
            name = _get_organism_name("eco")

        assert name == "Escherichia coli K-12 MG1655"

    def test_get_organism_name_not_found(self):
        """Returns code if organism not found."""
        mock_response = MagicMock()
        mock_response.text = ""

        with patch("requests.get", return_value=mock_response):
            name = _get_organism_name("unknown")

        assert name == "unknown"

    def test_get_organism_name_handles_error(self):
        """Returns code on error."""
        with patch("requests.get", side_effect=Exception("Error")):
            name = _get_organism_name("eco")
        assert name == "eco"
