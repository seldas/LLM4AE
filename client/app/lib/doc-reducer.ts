import { act } from "react";
import { Annotation, AnnotationRelationships, HighlightedTerms, TextContext } from "./interfaces";
import { getCurrentDateString, splitIntoSentences } from "./util";

export interface DocState {
    file: File | null
    pages: string[];
    currentPageIndex: number;
    annotations: Annotation[];
    meta: Record<string, any>;
    highlightedTerms: HighlightedTerms;
    saveFileName: string;
};

export const initialDocState: DocState = {
    file: null,
    pages: [],
    currentPageIndex: 0,
    annotations: [],
    meta: {},
    highlightedTerms: {},
    saveFileName: ''
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
    payload: { annotation: Annotation }
};

export interface UpdateAnnotationDocAction {
    type: DocActionTypes.UPDATE_ANNOTATION;
    payload: { annotation: Annotation}
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
    ChangeVerificationDocAction
    ;


export function docReducer(state: DocState, action: DocActions ) {
    switch (action.type) {
        case DocActionTypes.CLEAR: {
            return {
                file: null,
                pages: [],
                currentPageIndex: 0,
                annotations: [],
                meta: {},
                highlightedTerms: {},
                saveFileName: '',
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
                saveFileName: `user-input-${getCurrentDateString()}`
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
            return {
                ...state,
                annotations: [...state.annotations, action.payload.annotation]
            };
        };

        case DocActionTypes.UPDATE_ANNOTATION: {
            const updatedAnnotations = state.annotations.map((a) => {
              if (
                a.textContext.text === action.payload.annotation.textContext.text &&
                a.textContext.start === action.payload.annotation.textContext.start &&
                a.textContext.end === action.payload.annotation.textContext.end &&
                a.label === action.payload.annotation.label // Add this check

              ) {
                
                return {
                  ...a,
                  note: action.payload.annotation.note,
                };
              }
              return a; // unchanged
            });
          
            // Check if we need to add a new annotation
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
          
            return {
              ...state,
              annotations: updatedAnnotations
            };
          }
          

        case DocActionTypes.REMOVE_ANNOTATION: {
            let newHighlightedTerms = {...state.highlightedTerms};
            const annotation = action.payload.annotation
            // console.log('Trying to remove:', annotation);
            const index = state.annotations.findIndex((a) =>
              a.textContext.text === annotation.textContext.text &&
              a.note === annotation.note &&
              a.textContext.start === annotation.textContext.start &&
              a.textContext.end === annotation.textContext.end  
            );
            newHighlightedTerms = { ...state.highlightedTerms, [annotation.textContext.text]: false }
            const newAnnotations = [...state.annotations]
            newAnnotations.splice(index, 1);
            return {
                ...state,
                highlightedTerms: newHighlightedTerms,
                annotations: newAnnotations,
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
                updatedAnnotations
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

        default:
            return state;
    } 
}