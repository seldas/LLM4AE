import { act } from "react";
import { Annotation, AnnotationRelationships, HighlightedTerms, TextContext } from "./interfaces";
import { getCurrentDateString, splitIntoSentences } from "./util";

export interface ActionRecord {
    id: string;
    type: 'add' | 'verify' | 'reject' | 'remove';
    annotation: Annotation;
    timestamp: number;
    prevAnnotation?: Annotation; // For update/verify/reject to restore previous state
}

export interface DocState {
    file: File | null
    pages: string[];
    currentPageIndex: number;
    annotations: Annotation[];
    meta: Record<string, any>;
    highlightedTerms: HighlightedTerms;
    saveFileName: string;
    actionHistory: ActionRecord[];
};

export const initialDocState: DocState = {
    file: null,
    pages: [],
    currentPageIndex: 0,
    annotations: [],
    meta: {},
    highlightedTerms: {},
    saveFileName: '',
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
    payload: { pages: string[], annotations: Annotation[], meta: Record<string, any>, fileName: string };
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
    CommitHistoryDocAction
    ;


export function docReducer(state: DocState, action: DocActions ) {
    switch (action.type) {
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
                pages: action.payload.pages,
                currentPageIndex: 0,
                annotations: action.payload.annotations,
                meta: action.payload.meta || {},
                highlightedTerms: {},
                saveFileName: action.payload.fileName.replace('.json', ''),
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
            } else if (actionToUndo.type === 'reject') {
                // Restore the previous state of the annotation
                if (actionToUndo.prevAnnotation) {
                    newAnnotations = newAnnotations.map(a => 
                        (a.textContext.start === actionToUndo.annotation.textContext.start &&
                         a.textContext.end === actionToUndo.annotation.textContext.end &&
                         a.label === actionToUndo.annotation.label) 
                         ? actionToUndo.prevAnnotation! : a
                    );
                }
            } else if (actionToUndo.type === 'verify') {
                // Verification involves adding a user annotation AND updating the AI one
                // Undo both: remove user annotation and restore AI one
                
                // 1. Remove user annotation (the one in actionToUndo.annotation)
                newAnnotations = newAnnotations.filter(a => 
                    !(a.textContext.start === actionToUndo.annotation.textContext.start &&
                      a.textContext.end === actionToUndo.annotation.textContext.end &&
                      a.label === actionToUndo.annotation.label &&
                      a.note === actionToUndo.annotation.note)
                );

                // 2. Restore prev AI annotation if exists
                if (actionToUndo.prevAnnotation) {
                    newAnnotations = newAnnotations.map(a => 
                        (a.textContext.start === actionToUndo.annotation.textContext.start &&
                         a.textContext.end === actionToUndo.annotation.textContext.end &&
                         a.label === actionToUndo.annotation.label &&
                         a.note === actionToUndo.prevAnnotation?.note) 
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

        default:
            return state;
    } 
}
