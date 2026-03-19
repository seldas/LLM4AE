import { Annotation } from "./interfaces";

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

const defaultLabelHues: { [key: string]: number } = {
    AE: 0,
    MAE: 10,
    'CAUSE OF DEATH': 40,
    DIAGNOSTIC: 50,
    STATUS: 70,
    'MEDICAL HISTORY': 90,
    IND: 110,
    'FAMILY HISTORY': 100,
    TEMPORAL: 200,
    AGE: 210,
    SEX: 210,
    DRUG: 250,
    SDRUG: 250,
    CDRUG: 280,
    DOSE:290,
    LAB :290,
    TREATMENT: 280,
    DISPOSITION: 285,
  };
  
export const generateOptionColors = (options: string[]): {
    [key: string]: string;
  } => {
    const colors: { [key: string]: string } = {};
    const saturation = 70;
    const lightness = 50;
  
    options.forEach((option) => {
      const label = option.toUpperCase();
      if (defaultLabelHues[label] !== undefined) {
        const hue = defaultLabelHues[label];
        colors[label] = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
      } else {
        colors[label] = `hsl(0, 0%, 80%)`; // light gray for custom types
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