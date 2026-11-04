import type { Metadata } from "next";
import NavigatorConsole from "@/components/navigator/NavigatorConsole";

export const metadata: Metadata = {
  title: "Bridgeline Navigator",
  description: "Bridgeline career navigator caseload and grant review.",
};

export default function NavigatorPage() {
  return <NavigatorConsole />;
}
