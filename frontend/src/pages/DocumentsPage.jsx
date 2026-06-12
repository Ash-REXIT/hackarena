import { useApp } from "../context/AppContext";
import UploadZone from "../components/documents/UploadZone";
import DocumentTable from "../components/documents/DocumentTable";

export default function DocumentsPage() {
  const { documents, uploadDocument } = useApp();

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold mb-1">Documents</h1>
        <p className="text-gray-400 text-sm">Upload and manage your private knowledge base.</p>
      </div>
      <UploadZone onUpload={uploadDocument} />
      <DocumentTable documents={documents} />
    </div>
  );
}
