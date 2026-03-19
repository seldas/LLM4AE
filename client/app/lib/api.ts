import axios, { AxiosResponse, AxiosRequestConfig, RawAxiosRequestHeaders } from 'axios';
import { Annotation, FileData } from './interfaces';

const client = axios.create({
  baseURL: '/api/',
});

export const getHistoryFile = async (fileName: string, curr_folder: string) => {
  try {
    const response: AxiosResponse = await client.get(`/history/${curr_folder}___${fileName}`)
    const data: FileData = response.data;
    return data;
  } catch (error) {
    console.error('Error loading history file:', error);
    const errorMessage = error instanceof Error ? error.message : "Unknown error occurred.";
    alert(`Failed to load the file: ${fileName}. Error: ${errorMessage}`);
  };
};

export const saveFile = async (
  fileName: string,
  pages: string[],
  annotations: Annotation[],
  curr_folder: string,
  meta: Record<string, any>
) => {
  try {
    await client.post('/save', {
      fileName,
      curr_folder,
      pages,
      annotations,
      meta,
    });
  } catch (error) {
    console.error('Error saving file:', error);
  }
};
