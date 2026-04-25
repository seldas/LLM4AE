import { Annotation } from "./interfaces";

const rawBasePath = process.env.NEXT_PUBLIC_BASE_PATH !== undefined ? process.env.NEXT_PUBLIC_BASE_PATH : "";
export const BASE_PATH = rawBasePath === "" ? "" : (rawBasePath.startsWith('/') ? rawBasePath : `/${rawBasePath}`).replace(/\/$/, '');
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE !== undefined ? process.env.NEXT_PUBLIC_API_BASE : "http://localhost:8862/api";

export const splitIntoSentences = (text: string): string[] => {
    const sentences = text.split(/(?:\n+|(?<=\.)\s+)/);
    // If the text is empty or doesn't match the regex, return an empty array or the original text.
    return sentences || [text];

};

export const extractPlainTextWithMapping = (html: string): { 
    plainText: string, mapping: number[] 
} => {
    const plainText = [];
    const mapping = [];

    let inTag = false;
    let textIndex = 0;

    for (let i = 0; i < html.length; i++) {
        const char = html[i];

        if (char === '<') {
            inTag = true;
        }

        if (!inTag) {
            plainText.push(char);
            mapping[textIndex] = i; // Map text index to original HTML index.
            textIndex++;
        }

        if (char === '>') {
            inTag = false;
        }
    }

    return { plainText: plainText.join(''), mapping };
};

export const getCurrentDateString = (): string => {
    const today = new Date();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    const year = today.getFullYear();
    return `${month}${day}${year}`;
};

const labelCategoryMap: { [key: string]: string } = {
    'R/O': 'DIAGNOSTIC',
    'BSYM': 'MEDICAL HISTORY',
    'SYMPTOM': 'AE',
    'SIGN': 'AE',
    'COD': 'CAUSE OF DEATH',
    'AGE': 'DEMOGRAPHIC',
    'SEX': 'DEMOGRAPHIC',
    'GENDER': 'DEMOGRAPHIC',
    'RACE': 'DEMOGRAPHIC',
    'ETHNICITY': 'DEMOGRAPHIC',
    'BIRTH': 'DEMOGRAPHIC',
    'TEMPO': 'TEMPORAL',
    'DATE': 'TEMPORAL',
    'TIME': 'TEMPORAL',
    'DURATION': 'TEMPORAL',
    'RELATIVE': 'TEMPORAL',
    'LATENCY': 'TEMPORAL',
    'FREQUENCY': 'TEMPORAL',
    'TEMPORAL SEQUENCE': 'TEMPORAL',
    'SDRUG': 'DRUG',
    'CDRUG': 'DRUG',
    'DOSE': 'DRUG',
    'ROUTE': 'DRUG',
};

const defaultLabelHues: { [key: string]: number } = {
    'AE': 0,
    'MAE': 10,
    'CAUSE OF DEATH': 40,
    'DIAGNOSTIC': 50,
    'STATUS': 70,
    'MEDICAL HISTORY': 90,
    'IND': 110,
    'FAMILY HISTORY': 100,
    'TEMPORAL': 200,
    'DEMOGRAPHIC': 210,
    'AGE': 210,
    'SEX': 210,
    'DRUG': 250,
    'LAB': 290,
    'TREATMENT': 280,
    'DISPOSITION': 285,
    'PROCEDURE': 320,
    'DEVICE': 340,
};
  
export const generateOptionColors = (options: string[]): {
    [key: string]: string;
  } => {
    const colors: { [key: string]: string } = {};
    const saturation = 70;
    const lightness = 50;
  
    options.forEach((option) => {
      const label = option.toUpperCase();
      const category = labelCategoryMap[label] || label;
      
      if (defaultLabelHues[category] !== undefined) {
        const hue = defaultLabelHues[category];
        colors[option] = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
      } else if (defaultLabelHues[label] !== undefined) {
        const hue = defaultLabelHues[label];
        colors[option] = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
      } else {
        // Generate a deterministic hue based on the label string
        let hash = 0;
        for (let i = 0; i < label.length; i++) {
          hash = label.charCodeAt(i) + ((hash << 5) - hash);
        }
        const hue = Math.abs(hash) % 360;
        colors[option] = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
      }
    });
  
    return colors;
  };
  


// Utility function to escape special regex characters.
export const escapeRegExp = (string: string): string => {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
};

export const capitalizeFirstLetter = (string: string): string => {
    return string.charAt(0).toUpperCase() + string.slice(1);
  }

export function instanceOfAnnotation(object: any): object is Annotation {
    return 'textContext' in object;
}

export function stripNewlines(str: string) {
    return str.replace(/[\\\r\n]+/g, "");
  }