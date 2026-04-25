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

export const saveAnnotationsToDb = async ({
  fileName,
  id,
  curr_folder,
  pages,
  annotations,
  meta,
}: SaveAnnotationsPayload) => {
  try {
    const identifier = id || `${curr_folder}___${fileName}`;
    const url = `/history/${encodeURIComponent(identifier)}${id ? `?project=${encodeURIComponent(curr_folder)}` : ''}`;
    const response = await client.post(
      url,
      {
        pages,
        annotations,
        meta,
      }
    );
    return response.data;
  } catch (error) {
    console.error('Error saving annotations to DB:', error);
    throw error;
  }
};
