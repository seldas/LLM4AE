export interface HoverNote {
    visible: boolean,
    x: number,
    y: number,
    text: string,
}

export interface FileData {
  pages: string[];
  annotations: Annotation[];
  meta: Record<string, any>;
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


export interface CaseMetadata {
  llm_status: 'idle' | 'working' | 'Done';
  bert_status: 'idle' | 'working' | 'Done';
  review_status: 'pending' | 'in_progress' | 'completed';
  [key: string]: any;
}

export interface Annotation {
    id?: number; // Now optional to accommodate new annotations
    textContext: TextContext,
    label: string,
    note: string
    disputed?: boolean
    adjudication?: string;
    relationships?: any;
}

export interface AnnotationOptions {
    [key: string]: string
}

export interface AnnotationOptionSet {
    [key: string]: AnnotationOptions
}

export interface AnnotationGuideline {
    label: string;
    description: string;
    rule: string;
    color?: string;
}

export interface HighlightedTerms {
    [key: string]: boolean
}

export interface ContextMenu {
    visible: boolean,
    x: number,
    y: number,
    type: 'annotation' | 'verification',
    start?: number,
    end?: number,
    options?: string[]
}

export interface SaveAnnotationsPayload {
  fileName?: string;
  id?: string;
  curr_folder: string;
  pages: string[];
  annotations: Annotation[];
  meta: Record<string, any>;
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
