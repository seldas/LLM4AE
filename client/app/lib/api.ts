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
    const response: AxiosResponse = await client.get(`/case/${id}`);
    const data: any = response.data;

    if (data && data.full_data) {
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

    return data as FileData;
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
