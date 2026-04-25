import { act } from "react";
import { Annotation, AnnotationRelationships, HighlightedTerms, TextContext, CaseMetadata } from "./interfaces";
import { getCurrentDateString, splitIntoSentences } from "./util";

export interface ActionRecord {
    id: string;
    type: 'add' | 'verify' | 'reject' | 'remove';
    annotation: Annotation;
    timestamp: number;
    prevAnnotation?: Annotation; // For update/verify/reject to restore previous state
}

export interface DocState {
    caseId: number | null;
    caseNumber: string;
    versionNumber: string;
    pages: string[];
    currentPageIndex: number;
    annotations: Annotation[];
    status: CaseMetadata;
    meta: Record<string, any>;
    highlightedTerms: HighlightedTerms;
    actionHistory: ActionRecord[];
};

export const initialDocState: DocState = {
    caseId: null,
    caseNumber: '',
    versionNumber: '',
    pages: [],
    currentPageIndex: 0,
    annotations: [],
    status: {
        llm_status: 'idle',
        bert_status: 'idle',
        review_status: 'pending'
    },
    meta: {},
    highlightedTerms: {},
    actionHistory: []
}

export enum DocActionTypes {
    CLEAR = "CLEAR",
    CHANGE = "CHANGE",
    UPLOAD = "UPLOAD",
    LOAD = "LOAD",
    PASTE_TEXT = "PASTE_TEXT",
    CHANGE_PAGE = "CHANGE_PAGE",
    NEXT_PAGE = "NEXT_PAGE",
    PREV_PAGE = "PREV_PAGE",
    ADD_ANNOTATION = "ADD_ANNOTATION",
    UPDATE_ANNOTATION = "UPDATE_ANNOTATION",
    REMOVE_ANNOTATION = "REMOVE_ANNOTATION",
    HIGHLIGHT_ALL = "HIGHLIGHT_ALL",
    SET_SAVE_FILE_NAME = "SET_SAVE_FILE_NAME",
    ADD_RELATION = "ADD_RELATION",
    CHANGE_VERIFICATION ="CHANGE_VERIFICATION",
    UNDO_ACTION = "UNDO_ACTION",
    COMMIT_HISTORY = "COMMIT_HISTORY",
    SYNC_ANNOTATION_ID = "SYNC_ANNOTATION_ID",
    APPEND_ANNOTATIONS = "APPEND_ANNOTATIONS",
};

export interface APPEND_ANNOTATIONS_Action {
    type: DocActionTypes.APPEND_ANNOTATIONS;
    payload: { annotations: Annotation[] }
};

export interface SYNC_ANNOTATION_ID_Action {
    type: DocActionTypes.SYNC_ANNOTATION_ID;
    payload: { tempId: string, realId: number }
};

export interface ClearDocAction {
    type: DocActionTypes.CLEAR;
};

export interface UploadDocAction {
    type: DocActionTypes.UPLOAD;
    payload: { pages: string[] };
};

export interface ChangeDocAction {
    type: DocActionTypes.CHANGE;
    payload: { file: File };
};

export interface LoadDocAction {
    type: DocActionTypes.LOAD;
    payload: { 
        pages: string[], 
        annotations: Annotation[], 
        meta: Record<string, any>, 
        fileName: string,
        caseId?: number,
        caseNumber?: string,
        versionNumber?: string,
        status?: CaseMetadata
    };
};

export interface PasteTextDocAction {
    type: DocActionTypes.PASTE_TEXT;
    payload: { text: string };
};

export interface NextPageDocAction {
    type: DocActionTypes.NEXT_PAGE
};

export interface PrevPageDocAction {
    type: DocActionTypes.PREV_PAGE
};

export interface ChangePageDocAction {
    type: DocActionTypes.CHANGE_PAGE;
    payload: { index: number }
};

export interface AddAnnotationDocAction {
    type: DocActionTypes.ADD_ANNOTATION;
    payload: { annotation: Annotation, historyType?: 'add' | 'verify', prevAnnotation?: Annotation }
};

export interface UpdateAnnotationDocAction {
    type: DocActionTypes.UPDATE_ANNOTATION;
    payload: { annotation: Annotation, historyType?: 'verify' | 'reject' }
};

export interface RemoveAnnotationDocAction {
    type: DocActionTypes.REMOVE_ANNOTATION;
    payload: { annotation: Annotation }
};

export interface HighlightAllDocAction {
    type: DocActionTypes.HIGHLIGHT_ALL;
    payload: { term: string }
};

export interface SetSaveFileNameDocAction {
    type: DocActionTypes.SET_SAVE_FILE_NAME;
    payload: { name: string }
};

export interface AddRelationDocAction {
    type: DocActionTypes.ADD_RELATION;
    payload: { annotation: Annotation, relation: string, context: TextContext }
};
export interface ChangeVerificationDocAction {
    type: DocActionTypes.CHANGE_VERIFICATION;
    payload: { annotation: Annotation, disputed: boolean }
};

export interface UndoActionDocAction {
    type: DocActionTypes.UNDO_ACTION;
    payload: { actionId: string }
};

export interface CommitHistoryDocAction {
    type: DocActionTypes.COMMIT_HISTORY;
};

export type DocActions = 
    ClearDocAction |
    ChangeDocAction |
    UploadDocAction |
    LoadDocAction |
    PasteTextDocAction |
    ChangePageDocAction |
    NextPageDocAction | 
    PrevPageDocAction |
    AddAnnotationDocAction |
    UpdateAnnotationDocAction |
    RemoveAnnotationDocAction |
    HighlightAllDocAction |
    SetSaveFileNameDocAction |
    AddRelationDocAction |
    ChangeVerificationDocAction |
    UndoActionDocAction |
    CommitHistoryDocAction |
    APPEND_ANNOTATIONS_Action |
    SYNC_ANNOTATION_ID_Action
    ;


export function docReducer(state: DocState, action: DocActions ) {
    switch (action.type) {
        case DocActionTypes.APPEND_ANNOTATIONS: {
            // Filter out any annotations that are already in the state (by ID if available, otherwise by context)
            const existingIds = new Set(state.annotations.map(a => a.id).filter(id => id !== undefined));
            const newAnnotations = action.payload.annotations.filter(a => !existingIds.has(a.id));
            
            return {
                ...state,
                annotations: [...state.annotations, ...newAnnotations]
            };
        };

        case DocActionTypes.CLEAR: {
            return {
                ...initialDocState
            };
        };

        case DocActionTypes.CHANGE: {
            const fileNameWithoutSuffix = action.payload.file.name.replace(/\.[^/.]+$/, '.Annotated');
            return {
                ...state,
                file: action.payload.file,
                saveFileName: fileNameWithoutSuffix,
            };
        };

        case DocActionTypes.UPLOAD: {
            return {
                ...state,
                pages: action.payload.pages,
                currentPageIndex: 0,
                annotations: [],
                meta: {},
                highlightedTerms: {},
                actionHistory: [],
            };
        };

        case DocActionTypes.LOAD: {
            return {
                ...state,
                caseId: action.payload.caseId || null,
                caseNumber: action.payload.caseNumber || '',
                versionNumber: action.payload.versionNumber || '',
                pages: action.payload.pages || [],
                currentPageIndex: 0,
                annotations: action.payload.annotations || [],
                status: {
                    llm_status: action.payload.status?.llm_status || 'idle',
                    bert_status: action.payload.status?.bert_status || 'idle',
                    review_status: action.payload.status?.review_status || 'pending',
                },
                meta: action.payload.meta || {},
                highlightedTerms: {},
                actionHistory: [],
            };
        };

        case DocActionTypes.PASTE_TEXT: {
            const sentences = splitIntoSentences(action.payload.text);
            const formattedText = sentences.map(sentence => `${sentence}`).join('');
            const newPages: string[] = [formattedText]
            return {
                ...state,
                pages: newPages,
                currentPageIndex: 0,
                annotations: [],
                meta: {},
                saveFileName: `user-input-${getCurrentDateString()}`,
                actionHistory: [],
            };
        };

        case DocActionTypes.NEXT_PAGE: {
            if (state.currentPageIndex < state.pages.length - 1) {
                return {
                    ...state,
                    currentPageIndex: state.currentPageIndex + 1
                }
            };
            return state;
        };

        case DocActionTypes.PREV_PAGE: {
            if (state.currentPageIndex > 0) {
                return {
                    ...state,
                    currentPageIndex: state.currentPageIndex - 1
                }
            };
            return state;
        };

        case DocActionTypes.CHANGE_PAGE: {
            return {
                ...state,
                currentPageIndex: action.payload.index
            };
        };

        case DocActionTypes.ADD_ANNOTATION: {
            const newHistory: ActionRecord[] = action.payload.historyType ? [
                {
                    id: Math.random().toString(36).substr(2, 9),
                    type: action.payload.historyType,
                    annotation: action.payload.annotation,
                    timestamp: Date.now(),
                    prevAnnotation: action.payload.prevAnnotation
                },
                ...state.actionHistory
            ] : state.actionHistory;

            return {
                ...state,
                annotations: [...state.annotations, action.payload.annotation],
                actionHistory: newHistory
            };
        };

        case DocActionTypes.UPDATE_ANNOTATION: {
            let prevAnnotation: Annotation | undefined;
            
            const updatedAnnotations = state.annotations.map((a) => {
              if (
                a.textContext.text === action.payload.annotation.textContext.text &&
                a.textContext.start === action.payload.annotation.textContext.start &&
                a.textContext.end === action.payload.annotation.textContext.end &&
                a.label === action.payload.annotation.label 
              ) {
                prevAnnotation = { ...a };
                return {
                  ...a,
                  note: action.payload.annotation.note,
                  relationships: action.payload.annotation.relationships,
                };
              }
              return a; 
            });
          
            const annotationExists = updatedAnnotations.some(
              a => 
                a.textContext.text === action.payload.annotation.textContext.text &&
                a.textContext.start === action.payload.annotation.textContext.start &&
                a.textContext.end === action.payload.annotation.textContext.end &&
                a.label === action.payload.annotation.label
            );
          
            if (!annotationExists) {
              updatedAnnotations.push(action.payload.annotation);
            }

            const newHistory: ActionRecord[] = action.payload.historyType ? [
                {
                    id: Math.random().toString(36).substr(2, 9),
                    type: action.payload.historyType,
                    annotation: action.payload.annotation,
                    timestamp: Date.now(),
                    prevAnnotation: prevAnnotation
                },
                ...state.actionHistory
            ] : state.actionHistory;
          
            return {
              ...state,
              annotations: updatedAnnotations,
              actionHistory: newHistory
            };
          }
          

        case DocActionTypes.REMOVE_ANNOTATION: {
            const annotation = action.payload.annotation
            const index = state.annotations.findIndex((a) =>
              a.textContext.text === annotation.textContext.text &&
              a.note === annotation.note &&
              a.textContext.start === annotation.textContext.start &&
              a.textContext.end === annotation.textContext.end &&
              (a.label === annotation.label || (a.label.toUpperCase() === annotation.label.toUpperCase()))
            );

            if (index === -1) return state;

            const removedAnnotation = state.annotations[index];
            const newAnnotations = [...state.annotations]
            newAnnotations.splice(index, 1);

            const newHistory: ActionRecord[] = [
                {
                    id: Math.random().toString(36).substr(2, 9),
                    type: 'remove',
                    annotation: removedAnnotation,
                    timestamp: Date.now()
                },
                ...state.actionHistory
            ];

            return {
                ...state,
                highlightedTerms: { ...state.highlightedTerms, [annotation.textContext.text]: false },
                annotations: newAnnotations,
                actionHistory: newHistory
            };
        };

        case DocActionTypes.HIGHLIGHT_ALL: {
            return {
                ...state,
                highlightedTerms: { 
                    ...state.highlightedTerms, 
                    [action.payload.term]: !state.highlightedTerms[action.payload.term]}
            };
        };

        case DocActionTypes.SET_SAVE_FILE_NAME: {
            return {
                ...state,
                saveFileName: action.payload.name,
            };
        };

        case DocActionTypes.ADD_RELATION: {
            const newAnnotation = action.payload.annotation
            newAnnotation.relationships[action.payload.relation as keyof AnnotationRelationships] = action.payload.context;

            const updatedAnnotations = [...state.annotations];
            const index = updatedAnnotations.findIndex((a) => a == action.payload.annotation);
            updatedAnnotations[index] = newAnnotation;
            return {
                ...state,
                annotations: updatedAnnotations
            }
        };

        case DocActionTypes.CHANGE_VERIFICATION: {
          const { annotation, disputed } = action.payload;
        
          const updatedAnnotations = state.annotations.map((a) => {
            const isMatch =
              a.textContext.start === annotation.textContext.start &&
              a.textContext.end === annotation.textContext.end &&
              a.textContext.text === annotation.textContext.text &&
              a.note === annotation.note;
        
            if (isMatch) {
              return { ...a, disputed };
            }
            return a;
          });
        
          return {
            ...state,
            annotations: updatedAnnotations,
          };
        }

        case DocActionTypes.UNDO_ACTION: {
            const actionToUndo = state.actionHistory.find(a => a.id === action.payload.actionId);
            if (!actionToUndo) return state;

            let newAnnotations = [...state.annotations];

            if (actionToUndo.type === 'add') {
                // Remove the added annotation
                newAnnotations = newAnnotations.filter(a => 
                    !(a.textContext.start === actionToUndo.annotation.textContext.start &&
                      a.textContext.end === actionToUndo.annotation.textContext.end &&
                      a.label === actionToUndo.annotation.label &&
                      a.note === actionToUndo.annotation.note)
                );
            } else if (actionToUndo.type === 'remove') {
                // Add back the removed annotation
                newAnnotations.push(actionToUndo.annotation);
            } else if (actionToUndo.type === 'reject' || actionToUndo.type === 'verify') {
                // Restore the previous state of the annotation
                if (actionToUndo.prevAnnotation) {
                    newAnnotations = newAnnotations.map(a => 
                        (a.textContext.start === actionToUndo.annotation.textContext.start &&
                         a.textContext.end === actionToUndo.annotation.textContext.end &&
                         a.label === actionToUndo.annotation.label &&
                         a.note === actionToUndo.annotation.note) 
                         ? actionToUndo.prevAnnotation! : a
                    );
                }
            }

            return {
                ...state,
                annotations: newAnnotations,
                actionHistory: state.actionHistory.filter(a => a.id !== action.payload.actionId)
            };
        }

        case DocActionTypes.COMMIT_HISTORY: {
            return {
                ...state,
                actionHistory: []
            };
        }

        case DocActionTypes.SYNC_ANNOTATION_ID: {
            const { tempId, realId } = action.payload;
            const updatedAnnotations = state.annotations.map(a => {
                // If the annotation doesn't have an ID yet, it's a candidate for sync.
                // We use a combination of text, start, and end as a pseudo-temp-id.
                // In a more robust implementation, we'd add a dedicated tempId field to the Annotation interface.
                return a; 
            });
            // For now, we'll rely on the re-fetching or surgical replacement in the component.
            return state;
        }

        default:
            return state;
    } 
}
