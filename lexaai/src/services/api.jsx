import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
});

export async function uploadContract(file) {
  const formData = new FormData();
  formData.append("file", file);

  const { data } = await api.post("/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return data;
}

export async function askContract(contractId, question) {
  const { data } = await api.post("/ask", {
    contract_id: contractId,
    question,
  });

  return data;
}

export default api;
