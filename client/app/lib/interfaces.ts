export interface HoverNote {
    visible: boolean,
    x: number,
    y: number,
    text: string,
}

export interface ProjectEntry {
  folderName: string;
  fileName: string;
  records: any[];
  totalCount?: number;
  limit?: number;
  offset?: number;
}

export interface FileStats {
  meta?: any;
  counts?: { [key: string]: number };
}

export interface MetaRecord {
  annotate_filename?: string;
  folderName?: string;
  meta?: any;
  counts?: { [key: string]: number | undefined };
  [key: string]: any;
}


export interface Annotation {
    id?: number;
    textContext: TextContext,
    label: string,
    note: string
    relationships: AnnotationRelationships
    disputed?: boolean
    adjudication?: string;
}

export interface AnnotationOptions {
    [key: string]: string
}

export interface AnnotationOptionSet {
    [key: string]: AnnotationOptions
}

export interface HighlightedTerms {
    [key: string]: boolean
}

export interface ContextMenu {
    visible: boolean,
    x: number,
    y: number,
    type: 'annotation' | 'relationship' | 'verification',
    start?: number,
    end?: number
}

export interface SaveAnnotationsPayload {
  id?: string;
  curr_folder: string;
  pages: string[];
  annotations: Annotation[];
  meta: Record<string, any>;
}

export interface AnnotationRelationships {
    latency?: TextContext,
    date?: TextContext,
    time?: TextContext,
    frequency?: TextContext,
    temporal_sequence?: TextContext,
    span?: TextContext,
    relatives?: TextContext
}

export interface TextContext {
    page: number,
    text: string,
    start?: number,
    end?: number,
    disputed?: false
}

export interface oldAnnotation {
    end?: number,
    label: string,
    note: string,
    page: string,
    start?: number,
    text: string
}

export enum AnnotationFilterOptions {
    SME1="SME1",
    SME2="SME2",
    Disputed="Disputed",
    Undisputed="Undisputed"
}

export type AnnotationFilters = {
    [key in keyof typeof AnnotationFilterOptions]: boolean
}