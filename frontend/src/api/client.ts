import axios from "axios";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  timeout: 30_000,
});

apiClient.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error),
);

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      console.error(
        `API error ${error.response.status}:`,
        error.response.data,
      );
    } else if (error.request) {
      console.error("Network error: no response received");
    }
    return Promise.reject(error);
  },
);

export default apiClient;
