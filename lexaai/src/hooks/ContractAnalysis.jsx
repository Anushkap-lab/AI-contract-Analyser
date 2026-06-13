import { useState } from "react";
import { analyseContract} from "../services/api";

export function useContractAnalysis() {
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState(null);
  const [error, setError]       = useState(null);

  const analyse = async (file) => {
    setLoading(true);
    setError(null);
    try {
      const data = await analyseContract(file);
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.message || "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return { analyse, loading, result, error };
}
