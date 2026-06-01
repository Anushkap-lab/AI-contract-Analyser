import UploadZone from "./components/Upload";
import ResultsDashboard from "./components/dashboard";
import AskPanel from "./components/Panel";
import HistoryPanel from "./components/History";
import { useContractAnalysis } from "./hooks/ContractAnalysis";
import Skeleton from './components/structure'

export default function App() {
  const {
    analyse,
    loading,
    result,
    error,
    history,
    selectHistoryItem,
    deleteHistoryItem,
    clearHistory,
  } = useContractAnalysis();

  return (
    <div className="app-shell min-h-screen bg-gray-50 font-sans text-gray-950 dark:bg-gray-950 dark:text-gray-100">
      <div className="page mx-auto max-w-xl px-4 py-10">
     
        </div>
      </div>
    
  );
}
