import axios from "axios";

// No global request timeout: document conversion and LaTeX compilation of
// large research papers can legitimately run for several minutes, and a fixed
// 30 s cap aborted them mid-way.  Individual short requests can still opt into
// their own timeout per call; long-running endpoints (convert/compile) pass
// `timeout: 0` explicitly so a successful long run is never terminated.
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  timeout: 0,
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
