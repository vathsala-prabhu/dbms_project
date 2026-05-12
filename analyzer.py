from Bio.Seq import Seq
from Bio import SeqIO
import io
from database import fetch_all_mutations

ETHNICITY_RISK_MODIFIERS = {
    'rs334':       {'Sub-Saharan African': 2.0, 'Mediterranean': 1.4},
    'rs1799966':   {'Ashkenazi Jewish': 3.0},
    'rs113993960': {'Northern European': 1.8, 'Ashkenazi Jewish': 1.5},
    'rs28897672':  {'Ashkenazi Jewish': 3.0, 'Northern European': 1.3},
    'rs429358':    {'European': 1.5},
    'rs6025':      {'European': 2.0},
}

PHARMA_SNP_IDS = {
    'rs1799853', 'rs1057910', 'rs9923231', 'rs4986893',
    'rs3892097', 'rs4149056', 'rs4363657', 'rs1800460',
}


def clean_sequence(raw_sequence: str) -> str:
    return ''.join(ch for ch in raw_sequence.upper() if ch in 'ATCGN')


def parse_fasta(file_content: str) -> str:
    try:
        fasta_io = io.StringIO(file_content)
        records  = list(SeqIO.parse(fasta_io, "fasta"))
        if records:
            return str(records[0].seq).upper()
    except Exception as e:
        print(f"FASTA parse error: {e}")
    return clean_sequence(file_content)


def get_reverse_complement(sequence: str) -> str:
    return str(Seq(sequence).reverse_complement())


def detect_zygosity(sequence: str, pattern: str, reverse_comp: str) -> str:
    fwd = sequence.count(pattern)
    rev = reverse_comp.count(pattern)
    if fwd >= 1 and rev >= 1:
        return 'Homozygous'
    if fwd >= 1 or rev >= 1:
        return 'Heterozygous'
    return 'Unknown'


def detect_compound_het(matches: list) -> list:
    from collections import defaultdict
    gene_map = defaultdict(list)
    for m in matches:
        gene_map[m['gene']].append(m)

    compound_hets = []
    for gene, muts in gene_map.items():
        if len(muts) >= 2:
            for i in range(len(muts)):
                for j in range(i + 1, len(muts)):
                    compound_hets.append({
                        'gene':      gene,
                        'snp_a':     muts[i]['snp_id'],
                        'snp_b':     muts[j]['snp_id'],
                        'disease_a': muts[i]['disease'],
                        'disease_b': muts[j]['disease'],
                        'note': (
                            f"Compound heterozygosity detected in {gene}: "
                            f"{muts[i]['snp_id']} + {muts[j]['snp_id']} may produce "
                            f"disease even if neither variant is homozygous."
                        )
                    })
    return compound_hets


def apply_population_risk(matches: list, ethnicity: str) -> list:
    if not ethnicity:
        return matches
    for m in matches:
        mod = ETHNICITY_RISK_MODIFIERS.get(str(m['snp_id']), {})
        m['population_modifier'] = mod.get(ethnicity, 1.0)
        if m['population_modifier'] > 1.0:
            m['population_note'] = (
                f"Risk elevated {m['population_modifier']}× for {ethnicity} ancestry."
            )
        else:
            m['population_note'] = None
    return matches


def build_pharma_report(matches: list) -> list:
    pharma = []
    for m in matches:
        if str(m['snp_id']) in PHARMA_SNP_IDS:
            pharma.append({
                'snp_id':      m['snp_id'],
                'gene':        m['gene'],
                'drug_impact': m['disease'],
                'risk_level':  m['risk_level'],
                'zygosity':    m.get('zygosity', 'Unknown'),
                'description': m['description'],
                'recommendation': _pharma_recommendation(
                    str(m['snp_id']), m.get('zygosity', 'Unknown')
                )
            })
    return pharma


def _pharma_recommendation(snp_id: str, zygosity: str) -> str:
    recs = {
        'rs1799853': "Consider 25–50% dose reduction for warfarin. Monitor INR closely.",
        'rs1057910': "CYP2C9*3: Reduce warfarin dose by 50–75%. High bleeding risk at standard doses.",
        'rs9923231': "VKORC1 sensitive variant. Use algorithm-based warfarin dosing.",
        'rs4986893': "Clopidogrel poor metaboliser. Consider alternative antiplatelet.",
        'rs3892097': "CYP2D6 variant. Codeine/tramadol may be ineffective or toxic.",
        'rs4149056': "SLCO1B1: Avoid high-dose simvastatin. Switch to pravastatin or rosuvastatin.",
        'rs4363657': "Intermediate statin transporter. Monitor for myopathy at simvastatin >40mg.",
        'rs1800460': "TPMT variant: Thiopurine dose MUST be reduced. Risk of fatal myelosuppression.",
    }
    base = recs.get(snp_id, "Consult pharmacist before prescribing affected medications.")
    if zygosity == 'Homozygous':
        base += " Homozygous carrier — effect is likely more severe."
    return base


def _infer_risk(mutation_type: str, original_base: str, mutated_base: str) -> str:
    """Infer a risk level from mutation properties."""
    if not mutation_type:
        return 'Low'
    mt = mutation_type.lower()
    if 'deletion' in mt or 'frameshift' in mt or 'nonsense' in mt:
        return 'High'
    if 'insertion' in mt or 'duplication' in mt:
        return 'Medium'
    return 'Low'


def analyze_dna(dna_sequence: str, ethnicity: str = None) -> dict:
    sequence = clean_sequence(dna_sequence)

    if len(sequence) < 10:
        return {"error": "Sequence too short. Please provide at least 10 base pairs."}

    if not all(ch in set('ATCGN') for ch in sequence):
        return {"error": "Invalid characters in sequence. Only A, T, C, G, N are allowed."}

    total   = len(sequence)
    a_count = sequence.count('A')
    t_count = sequence.count('T')
    c_count = sequence.count('C')
    g_count = sequence.count('G')
    n_count = sequence.count('N')
    gc_content = round(((g_count + c_count) / total) * 100, 2) if total > 0 else 0
    at_content = round(((a_count + t_count) / total) * 100, 2) if total > 0 else 0

    stats = {
        "length":     total,
        "gc_content": gc_content,
        "at_content": at_content,
        "n_count":    n_count,
        "base_counts": {"A": a_count, "T": t_count, "C": c_count, "G": g_count}
    }

    mutations    = fetch_all_mutations()
    reverse_comp = get_reverse_complement(sequence)
    matches      = []

    for mutation in mutations:
        # Build a pattern from mutated_base (new schema)
        # Fall back to mutation_sequence if present (old schema)
        pattern = (
            mutation.get('mutated_base') or
            mutation.get('mutation_sequence') or
            ''
        ).upper().strip()

        # Skip patterns that are too short or are just dashes (deletions)
        if not pattern or len(pattern) < 2 or pattern == '-':
            continue

        # Only keep DNA characters
        pattern = ''.join(ch for ch in pattern if ch in 'ATCGN')
        if len(pattern) < 2:
            continue

        found_forward = pattern in sequence
        found_reverse = pattern in reverse_comp

        if found_forward or found_reverse:
            position = sequence.find(pattern) if found_forward else reverse_comp.find(pattern)
            zygosity = detect_zygosity(sequence, pattern, reverse_comp)

            # Support both old schema (snp_id, gene, disease, risk_level, description)
            # and new schema (mutation_id, mutation_type, original_base, mutated_base)
            snp_id      = mutation.get('snp_id') or str(mutation.get('mutation_id', ''))
            gene        = mutation.get('gene') or mutation.get('gene_name') or 'Unknown'
            disease     = mutation.get('disease') or mutation.get('mutation_type') or 'Unknown'
            risk_level  = mutation.get('risk_level') or _infer_risk(
                mutation.get('mutation_type', ''),
                mutation.get('original_base', ''),
                mutation.get('mutated_base', '')
            )
            description = mutation.get('description') or (
                f"Mutation type: {mutation.get('mutation_type', 'Unknown')} | "
                f"Position: {mutation.get('position', '?')} | "
                f"{mutation.get('original_base', '?')} → {mutation.get('mutated_base', '?')}"
            )

            match_obj = {
                "snp_id":      snp_id,
                "gene":        gene,
                "disease":     disease,
                "risk_level":  risk_level,
                "description": description,
                "category":    mutation.get('category') or mutation.get('mutation_type'),
                "chromosome":  mutation.get('chromosome'),
                "strand":      "Forward" if found_forward else "Reverse Complement",
                "position":    position,
                "zygosity":    zygosity,
            }
            matches.append(match_obj)

    matches        = apply_population_risk(matches, ethnicity)
    compound_hets  = detect_compound_het(matches)
    pharma_report  = build_pharma_report(matches)
    clinical_matches = [m for m in matches if str(m['snp_id']) not in PHARMA_SNP_IDS]
    risk_summary   = compute_risk_summary(clinical_matches)

    return {
        "sequence_stats":   stats,
        "matches":          matches,
        "total_matches":    len(matches),
        "clinical_matches": clinical_matches,
        "compound_hets":    compound_hets,
        "pharma_report":    pharma_report,
        "risk_summary":     risk_summary,
    }


def compute_risk_summary(matches: list) -> dict:
    if not matches:
        return {
            "overall_risk":      "None Detected",
            "high_risk_count":   0,
            "medium_risk_count": 0,
            "low_risk_count":    0,
            "recommendation":    "No known disease-associated mutations detected in this sequence."
        }

    high   = sum(1 for m in matches if m['risk_level'] == 'High')
    medium = sum(1 for m in matches if m['risk_level'] == 'Medium')
    low    = sum(1 for m in matches if m['risk_level'] == 'Low')

    if high > 0:
        overall = "High"
        rec = "High-risk mutations detected. Immediate genetic counselling is strongly recommended."
    elif medium > 0:
        overall = "Medium"
        rec = "Moderate-risk mutations found. Consult a healthcare provider for further evaluation."
    else:
        overall = "Low"
        rec = "Only low-risk variants detected. Routine health monitoring is advised."

    return {
        "overall_risk":      overall,
        "high_risk_count":   high,
        "medium_risk_count": medium,
        "low_risk_count":    low,
        "recommendation":    rec
    }