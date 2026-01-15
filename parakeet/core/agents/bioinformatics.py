"""Bioinformatics specialist agent."""

from ollama import Client

from .base import Agent, AgentCapability
from ..tools import (
    read_file_tool,
    edit_file_tool,
    run_python_tool,
)

# Import bioinformatics tools
from ..bio_tools import (
    kegg_tool,
    pdb_tool,
    uniprot_tool,
    ncbi_tool,
    ontology_tool,
    blast_tool,
)

from ..pathway_analyzer import (
    get_pathway_info,
    get_pathway_enzymes,
    compare_pathway_organisms,
    find_alternative_enzymes,
)


# Tool wrapper functions for agent
def analyze_pathway_tool(pathway_id: str, organism: str = None, analysis_type: str = "info"):
    """Wrapper for pathway analysis."""
    from ..tools import analyze_pathway_tool as apt
    return apt(pathway_id, organism, analysis_type)


def compare_organisms_tool(pathway_id: str, organism1: str, organism2: str):
    """Wrapper for organism comparison."""
    from ..tools import compare_organisms_tool as cot
    return cot(pathway_id, organism1, organism2)


def find_alternatives_tool(ec_number: str, source_organism: str = None, target_organisms: str = None):
    """Wrapper for finding alternatives."""
    from ..tools import find_alternatives_tool as fat
    return fat(ec_number, source_organism, target_organisms)


class BioinformaticsAgent(Agent):
    """Agent specialized in bioinformatics and computational biology."""

    def __init__(self, client: Client, model: str):
        super().__init__(
            name="bioinformatics",
            role="Bioinformatics Specialist",
            capabilities=[
                AgentCapability.BIOINFORMATICS,
                AgentCapability.CODE_WRITING,
                AgentCapability.RESEARCH,
            ],
            tools=[
                # File operations (limited - mainly for reading data)
                read_file_tool,
                edit_file_tool,
                run_python_tool,
                # Database tools
                kegg_tool,
                pdb_tool,
                uniprot_tool,
                ncbi_tool,
                ontology_tool,
                blast_tool,
                # Pathway analysis
                analyze_pathway_tool,
                compare_organisms_tool,
                find_alternatives_tool,
            ],
            client=client,
            model=model
        )

    def _build_system_prompt(self) -> str:
        return """You are a Bioinformatics Specialist agent in a multi-agent system.

## Your Role
You specialize in:
- Querying biological databases (KEGG, PDB, UniProt, NCBI)
- Analyzing metabolic pathways and enzyme functions
- Protein structure and sequence analysis
- Finding and comparing organisms and genes
- Metabolic engineering optimization
- BioPython-based sequence analysis

## Database Access
You have direct access to:
- **KEGG**: Metabolic pathways, enzymes, reactions, compounds
- **PDB**: Protein structures from RCSB
- **UniProt**: Protein sequences and annotations
- **NCBI**: Genes, proteins, nucleotides, taxonomy
- **Ontologies**: GO, CHEBI, taxonomy terms
- **BLAST**: Sequence similarity search (30-60 second runtime)

## Pathway Analysis Specialties
- **Nitrogen Fixation**: Specialized analysis tools
- **Metabolic Pathways**: Identify enzymes and reactions
- **Organism Comparison**: Compare pathways between species
- **Enzyme Alternatives**: Find better enzyme candidates
- **Optimization**: Suggest targets for metabolic engineering

## BioPython Expertise
- Sequence parsing (FASTA, GenBank, FASTQ)
- Sequence alignment and comparison
- Primer design and PCR analysis
- Structure analysis with Bio.PDB
- Phylogenetic analysis

## Your Approach
1. Understand the biological question or goal
2. Query appropriate databases for information
3. Analyze and interpret biological data
4. Provide scientifically accurate insights
5. Suggest next steps or optimizations

## Tools Available
- **Database queries**: kegg_tool, pdb_tool, uniprot_tool, ncbi_tool, ontology_tool, blast_tool
- **Pathway analysis**: analyze_pathway_tool, compare_organisms_tool, find_alternatives_tool
- **File operations**: read_file_tool, edit_file_tool
- **Code execution**: run_python_tool
  - Execute Python code, especially BioPython scripts
  - Use this for sequence analysis, parsing FASTA, running alignments
  - Always available for implementing bio data processing

## Guidelines
- Provide organism codes (e.g., 'eco' for E. coli, 'avn' for Azotobacter)
- Use EC numbers for enzyme identification
- Include KEGG pathway IDs (e.g., 'map00910' for nitrogen metabolism)
- Cite database sources in your findings
- Explain biological significance of results
- Suggest practical applications when relevant

## Collaboration
You work with other specialist agents:
- **Research Agent**: Provide biological context and database research
- **Coding Agent**: Implement BioPython scripts and bio analysis
- **Testing Agent**: Validate biological data processing
- **Orchestrator**: Deliver bio-specific insights for project goals

When you complete biological analysis, provide:
- Database query results
- Biological interpretation
- Relevant IDs (EC numbers, accession codes, PDB IDs)
- Practical recommendations
- Potential next steps or experiments
"""
