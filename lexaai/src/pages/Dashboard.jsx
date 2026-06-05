import { Scale } from "lucide-react";
import UploadZone from "../components/Upload";
import ResultsDashboard from "../components/dashboard";
import AskPanel from "../components/Panel";
import { useContractAnalysis } from "../hooks/ContractAnalysis";
import Skeleton from "../components/structure";


export default function App() {
  const { analyse, loading, result, error } = useContractAnalysis();
  const contractId = result?.contract_id || result?.contractId || result?.id;

  return (
    <div className="app-shell">
        <div className={`centered-page ${result ? "has-result" : ""}`}>
          <div className="topbar">
            <div className="brand">
              <div className="brand-icon">
                <Scale size={22} strokeWidth={1.9} />
              </div>
              <div>
                <h1 className="brand-name">LexaAI</h1>
                <p className="brand-sub">Contract Intelligence</p>
              </div>
            </div>
          </div>

          <UploadZone onFileSelect={analyse} isLoading={loading} />

          {error && (
            <p className="mt-3 rounded-xl bg-red-50 px-4 py-2 text-sm text-red-600">
              {error}
            </p>
          )}

          {loading && (
            <div className="mt-6">
              <Skeleton />
            </div>
          )}

          {result && !loading && (
            <>
              <ResultsDashboard result={result} />
              {contractId && <AskPanel contractId={contractId} />}
            </>
          )}
        </div>
      </div>
    
  );
}

