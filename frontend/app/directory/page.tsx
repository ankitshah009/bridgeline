import type { Metadata } from "next";
import Directory from "@/components/directory/Directory";
import "./directory.css";

export const metadata: Metadata = {
  title: "Bridgeline Directory",
  description:
    "Free training programs, Bridgeline grant tiers and free help for San Francisco affordable-housing residents, searchable in any language.",
};

export default function DirectoryPage() {
  return <Directory />;
}
