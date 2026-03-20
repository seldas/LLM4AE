import axios, { AxiosResponse } from 'axios';
import { Annotation, FileData } from './interfaces';

const client = axios.create({
  baseURL: '/api/',
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

export interface SaveAnnotationsPayload {
  fileName: string;
  curr_folder: string;
  pages: string[];
  annotations: Annotation[];
  meta: Record<string, any>;
}

export const saveAnnotationsToDb = async ({
  fileName,
  curr_folder,
  pages,
  annotations,
  meta,
}: SaveAnnotationsPayload) => {
  try {
    const response = await client.post(
      `/history/${encodeURIComponent(curr_folder)}___${encodeURIComponent(fileName)}`,
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
