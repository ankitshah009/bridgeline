import type { Metadata } from "next";
import ImpactDashboard from "@/components/impact/ImpactDashboard";
import "./impact.css";

export const metadata: Metadata = {
  title: "Bridgeline Impact",
  description: "Bridgeline pilot outcomes and spending, aggregated live with Elasticsearch, with San Francisco open data context.",
};

export default function ImpactPage() {
  return <ImpactDashboard />;
}
