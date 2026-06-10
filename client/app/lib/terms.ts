const termDict : { [key: string]: string } = {
    'symptom': 'Sym',
    'family history': 'FHx', 
    'drug': 'Tx',
    'diagnosis': 'pDx',
    'second level diagnosis': 'sDx',
    'medical history': 'MHx',
    'cause of death': 'CoD',
    'rule out': 'R/O',
    'vaccine': 'Vax'
}

export const termMapper = (annotationTerms: string[], termLabel: string): string => { 
    const cleanedTermLabel = termLabel.toLowerCase().replace(/[/]/g, '').replace(/_/g, ' ');
    for (const officialTerm of annotationTerms) {
        const cleanedOfficialTerm = officialTerm.toLowerCase().replace(/[/]/g, '').replace(/_/g, ' ');

        if (cleanedTermLabel === cleanedOfficialTerm) {
            return officialTerm;
        } else if (cleanedTermLabel in termDict) {
            return termDict[cleanedTermLabel]
        }
    }
    return("");
};
