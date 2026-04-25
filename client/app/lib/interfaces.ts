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
    id: number; // Now mandatory for all DB-synced annotations
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
    type: 'annotation' | 'relationship' | 'verification',
    start?: number,
    end?: number
}

export interface SaveAnnotationsPayload {
  fileName?: string;
  id?: string;
  curr_folder: string;
  pages: string[];
  annotations: Annotation[];
  meta: Record<string, any>;
}

export interface AnnotationRelationships {
    latency?: number | TextContext,
    date?: number | TextContext,
    time?: number | TextContext,
    frequency?: number | TextContext,
    temporal_sequence?: number | TextContext,
    span?: number | TextContext,
    relatives?: number | TextContext,
    [key: string]: number | TextContext | undefined
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
