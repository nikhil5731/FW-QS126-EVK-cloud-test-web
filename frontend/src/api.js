import axios from 'axios';

export async function connectDevice(data) {
  try {
    const response = await axios.post('http://localhost:5000/connect', data);
    return response.data;
  } catch (error) {
    console.error('Error connecting to device:', error);
    throw error;
  }
}

export async function handleMode(mode, data) {
  try {
    const response = await axios.post(`http://localhost:5000/${mode}`, data);
    return response.data;
  } catch (error) {
    console.error(`Error handling mode ${mode}:`, error);
    throw error;
  }
}
