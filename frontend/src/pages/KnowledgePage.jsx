import { useApp } from "../context/AppContext";
import KnowledgeCard from "../components/knowledge/KnowledgeCard";

export default function KnowledgePage() {
  const { documents, health } = useApp();
  const retrievalMode = health?.encoderfile?.retrieval?.retrieval_mode || "keyword+filename";

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1">Knowledge Base</h1>
        <p className="text-gray-400 text-sm">Explore indexed private documents and embedding status.</p>
      </div>
      {documents.length === 0 ? (
        <div className="card p-12 text-center text-gray-500">No documents indexed yet.</div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {documents.map((doc) => (
            <KnowledgeCard key={doc.name} doc={doc} retrievalMode={retrievalMode} />
          ))}
        </div>
      )}
    </div>
  );
}
