import { Eye, RefreshCw, Trash2 } from "lucide-react";
import { formatBytes, formatDate } from "../../api/client";

function fileType(name) {
  const ext = name.split(".").pop()?.toUpperCase();
  return ext || "—";
}

export default function DocumentTable({ documents }) {
  if (!documents.length) {
    return (
      <div className="card p-12 text-center text-gray-500">
        No documents uploaded yet. Use the upload zone above.
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-gray-500">
              <th className="px-4 py-3">Document Name</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Size</th>
              <th className="px-4 py-3">Upload Date</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr key={doc.name} className="border-b border-border/50 hover:bg-surface-elevated/50">
                <td className="px-4 py-3 font-medium text-gray-200">{doc.name}</td>
                <td className="px-4 py-3 text-gray-400">{fileType(doc.name)}</td>
                <td className="px-4 py-3 text-gray-400">{formatBytes(doc.size_bytes)}</td>
                <td className="px-4 py-3 text-gray-400">{formatDate(doc.modified_at)}</td>
                <td className="px-4 py-3">
                  <span className="px-2 py-0.5 rounded-full text-xs bg-accent/10 text-accent border border-accent/20">
                    Indexed
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2 text-gray-500">
                    <button type="button" title="View" className="p-1 hover:text-accent">
                      <Eye className="w-4 h-4" />
                    </button>
                    <button type="button" title="Reindex" className="p-1 hover:text-warn">
                      <RefreshCw className="w-4 h-4" />
                    </button>
                    <button type="button" title="Delete" className="p-1 hover:text-danger opacity-40 cursor-not-allowed">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
