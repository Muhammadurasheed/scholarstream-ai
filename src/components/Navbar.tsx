import { Zap, Bell, User, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export const Navbar = () => {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-border/50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary/10 glow">
              <Zap className="w-5 h-5 text-primary" />
            </div>
            <span className="text-xl font-bold">
              Scholar<span className="gradient-text">Stream</span>
            </span>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            <a href="#" className="text-sm text-foreground hover:text-primary transition-colors">
              Discover
            </a>
            <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Saved
            </a>
            <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Applications
            </a>
            <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Resources
            </a>
          </div>

          {/* Right Side */}
          <div className="flex items-center gap-3">
            <Badge variant="live" className="hidden sm:flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-primary" />
              Live Updates
            </Badge>
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-primary" />
            </Button>
            <Button variant="glass" size="icon" className="hidden sm:flex">
              <User className="w-5 h-5" />
            </Button>
            <Button variant="ghost" size="icon" className="md:hidden">
              <Menu className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </div>
    </nav>
  );
};
