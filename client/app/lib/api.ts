import axios, { AxiosResponse } from 'axios';
import { Annotation, FileData, SaveAnnotationsPayload } from './interfaces';
import { API_BASE } from './util';

const client = axios.create({
  baseURL: `${API_BASE}`,
});

export const getHistoryFile = async (fileName: string, curr_folder: string) => {
  try {
    const response: AxiosResponse = await client.get(`/history/${curr_folder}___${fileName}`);
    const data: FileData = response.data;
    return data;
  } catch (error) {
    console.error('Error loading history file:', error);
    const errorMessage = error instanceof Error ? error.message : "Unknown error occurred.";
    alert(`Failed to load the file: ${fileName}. Error: ${errorMessage}`);
  }
};

export const getCaseById = async (id: string) => {
  try {
    console.log(`API: Fetching case ${id}`);
    const response: AxiosResponse = await client.get(`/case/${id}`);
    const data: any = response.data;
    console.log(`API: Received data for case ${id}. Annotations:`, data.annotations?.length);

    // Prioritize structured annotations from DB if present
    if (data && data.annotations && Array.isArray(data.annotations)) {
      console.log(`API: Using ${data.annotations.length} annotations from DB`);
    } else if (data && data.full_data) {
      try {
        const fullData = JSON.parse(data.full_data);
        data.annotations = fullData.annotations || [];
      } catch (error) {
        console.error('Error parsing full_data:', error);
        data.annotations = [];
      }
    } else {
      data.annotations = [];
    }

    if (data && data.meta) {
      try {
        data.meta = JSON.parse(data.meta);
      } catch (error) {
        console.error('Error parsing meta:', error);
        data.meta = {};
      }
    } else {
      data.meta = {};
    }

    if (data && data.pages) {
      try {
        data.pages = JSON.parse(data.pages);
      } catch (error) {
        console.error('Error parsing pages:', error);
        data.pages = [];
      }
    } else {
      data.pages = [];
    }

    return {
      ...data,
      status: {
        llm_status: data.llm_status || 'idle',
        bert_status: data.bert_status || 'idle',
        review_status: data.review_status || 'pending',
      }
    } as any;
  } catch (error) {
    console.error('Error loading case by ID:', error);
    const errorMessage = error instanceof Error ? error.message : "Unknown error occurred.";
    alert(`Failed to load the case with ID: ${id}. Error: ${errorMessage}`);
  }
};

export const createAnnotation = async (data: {
  case_id: number;
  label: string;
  start: number;
  end: number;
  text: string;
  note: string;
  relationships?: any;
}) => {
  try {
    const response = await client.post('/annotations/', data);
    return response.data;
  } catch (error) {
    console.error('Error creating annotation:', error);
    throw error;
  }
};

export const updateAnnotation = async (id: number, data: {
  label?: string;
  note?: string;
  relationships?: any;
  adjudication?: string;
}) => {
  try {
    const response = await client.patch(`/annotations/${id}/`, data);
    return response.data;
  } catch (error) {
    console.error('Error updating annotation:', error);
    throw error;
  }
};

export const deleteAnnotation = async (id: number) => {
  try {
    const response = await client.delete(`/annotations/${id}/`);
    return response.data;
  } catch (error) {
    console.error('Error deleting annotation:', error);
    throw error;
  }
};

export const getCaseAnnotations = async (caseId: number, limit = 500, offset = 0) => {
  try {
    const response: AxiosResponse = await client.get(`/case/${caseId}/annotations`, {
      params: { limit, offset }
    });
    return response.data as Annotation[];
  } catch (error) {
    console.error('Error loading annotations:', error);
    throw error;
  }
};

