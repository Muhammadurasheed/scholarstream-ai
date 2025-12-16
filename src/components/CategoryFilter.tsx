import { Badge } from "@/components/ui/badge";
import { GraduationCap, Coins, Briefcase, FlaskConical } from "lucide-react";

interface CategoryFilterProps {
  selectedCategory: string | null;
  onSelectCategory: (category: string | null) => void;
}

const categories = [
  { id: "scholarship", label: "Scholarships", icon: GraduationCap },
  { id: "grant", label: "Grants", icon: Coins },
  { id: "internship", label: "Internships", icon: Briefcase },
  { id: "research", label: "Research", icon: FlaskConical },
];

export const CategoryFilter = ({
  selectedCategory,
  onSelectCategory,
}: CategoryFilterProps) => {
  return (
    <div className="flex flex-wrap justify-center gap-3">
      <Badge
        variant={selectedCategory === null ? "active" : "category"}
        className="cursor-pointer px-4 py-2 text-sm"
        onClick={() => onSelectCategory(null)}
      >
        All Opportunities
      </Badge>
      {categories.map(({ id, label, icon: Icon }) => (
        <Badge
          key={id}
          variant={selectedCategory === id ? "active" : "category"}
          className="cursor-pointer px-4 py-2 text-sm flex items-center gap-2"
          onClick={() => onSelectCategory(id)}
        >
          <Icon className="w-4 h-4" />
          {label}
        </Badge>
      ))}
    </div>
  );
};
