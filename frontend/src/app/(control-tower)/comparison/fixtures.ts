import type { QuoteComparisonCardProps } from "@/components/control-tower/quote-comparison-card";

export const quoteComparisons: QuoteComparisonCardProps[] = [
  {
    carrierName: "Naviera del Caribe",
    price: "890.00 USD",
    pickupWindow: "2026-08-31 08:00 – 18:00",
    conditions: ["40ft dry container", "Standard handling", "Within mandate"],
    isWinner: true,
    status: { tone: "success", label: "ACTIVE" },
  },
  {
    carrierName: "Transportes Andinos SAS",
    price: "935.00 USD",
    pickupWindow: "2026-08-31 09:00 – 17:00",
    conditions: ["40ft dry container", "Within mandate"],
    isWinner: false,
    status: { tone: "neutral", label: "SUPERSEDED" },
  },
  {
    carrierName: "Logística Portuaria del Norte",
    price: "1,120.00 USD",
    pickupWindow: "2026-08-31 08:00 – 20:00",
    conditions: ["40ft dry container", "Exceeds price limit"],
    isWinner: false,
    status: { tone: "danger", label: "OUT OF MANDATE" },
  },
];
