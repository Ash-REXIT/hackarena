import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Brain,
  Cpu,
  FileSearch,
  Globe,
  Lock,
  Network,
  Shield,
  Sparkles,
  Upload,
} from "lucide-react";

const features = [
  { icon: Lock, title: "Private First Retrieval", desc: "Search your local documents before touching the internet." },
  { icon: Sparkles, title: "Explainable AI", desc: "Every answer shows confidence, sources, and reasoning." },
  { icon: Shield, title: "Privacy Score", desc: "Real-time score showing how much data stays local." },
  { icon: FileSearch, title: "Evidence-Based Responses", desc: "Perplexity-style citations from your private docs." },
  { icon: Network, title: "Multi-Agent Workflow", desc: "Retriever, Confidence, Decision, and Answer agents." },
  { icon: Globe, title: "Internet Fallback", desc: "Web search only when local confidence is low." },
];

const mozillaStack = [
  { icon: Cpu, name: "Encoderfile", desc: "Document embeddings and semantic retrieval.", color: "text-blue-400" },
  { icon: Brain, name: "Llamafile", desc: "Local reasoning and answer generation.", color: "text-purple-400" },
  { icon: Globe, name: "MCPD", desc: "External tools and web access.", color: "text-cyan-400" },
  { icon: Network, name: "Any-Agent", desc: "Orchestration and decision making.", color: "text-accent" },
];

export default function LandingPage() {
  return (
    <div className="max-w-6xl mx-auto px-4 pb-20">
      <section className="pt-20 pb-16 text-center bg-[radial-gradient(ellipse_at_50%_0%,rgba(212,98,42,0.14)_0%,transparent_55%)]">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-accent/30 bg-accent/10 text-accent text-xs font-medium mb-6">
            Mozilla AI Hackathon
          </div>
          <div className="text-5xl mb-3">🦊</div>
          <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-4 bg-gradient-to-b from-orange-100 via-accent-light to-accent bg-clip-text text-transparent">
            FoxZilla
          </h1>
          <p className="text-xl text-accent font-medium mb-4">Your Documents First. The Internet Second.</p>
          <p className="text-gray-400 max-w-2xl mx-auto mb-10 text-lg">
            A privacy-first explainable AI assistant that trusts your documents before trusting the internet.
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <Link to="/chat" className="btn-primary">
              Start Chatting <ArrowRight className="w-4 h-4" />
            </Link>
            <Link to="/documents" className="btn-secondary">
              <Upload className="w-4 h-4" /> Upload Documents
            </Link>
          </div>
        </motion.div>
      </section>

      <section className="py-16">
        <h2 className="text-2xl font-semibold text-center mb-10">Why FoxZilla</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map(({ icon: Icon, title, desc }, i) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
              className="card p-5 hover:border-accent/30 transition-colors"
            >
              <Icon className="w-8 h-8 text-accent mb-3" />
              <h3 className="font-semibold mb-2">{title}</h3>
              <p className="text-sm text-gray-400">{desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="py-16">
        <h2 className="text-2xl font-semibold text-center mb-3">Mozilla Technologies</h2>
        <p className="text-center text-gray-400 mb-10 text-sm">Built entirely on the Mozilla AI local-first stack</p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {mozillaStack.map(({ icon: Icon, name, desc, color }, i) => (
            <motion.div
              key={name}
              initial={{ opacity: 0, scale: 0.95 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
              className="card p-5 text-center"
            >
              <Icon className={`w-10 h-10 mx-auto mb-3 ${color}`} />
              <h3 className="font-semibold mb-2">{name}</h3>
              <p className="text-xs text-gray-400">{desc}</p>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  );
}
