import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
import Home from "@/pages/Home";
const About = lazy(() => import("@/pages/About"));
const Founders = lazy(() => import("@/pages/Founders"));
const Services = lazy(() => import("@/pages/Services"));
const Calculators = lazy(() => import("@/pages/Calculators"));
const HowItWorks = lazy(() => import("@/pages/HowItWorks"));
const Resources = lazy(() => import("@/pages/Resources"));
const Blog = lazy(() => import("@/pages/Blog"));
const BlogPost = lazy(() => import("@/pages/BlogPost"));
const Faq = lazy(() => import("@/pages/Faq"));
const Contact = lazy(() => import("@/pages/Contact"));
const Careers = lazy(() => import("@/pages/Careers"));
const Login = lazy(() => import("@/pages/Login"));
const Signup = lazy(() => import("@/pages/Signup"));
const Portal = lazy(() => import("@/pages/Portal"));
const PartnerPortal = lazy(() => import("@/pages/PartnerPortal"));
const Partners = lazy(() => import("@/pages/Partners"));
const Rates = lazy(() => import("@/pages/Rates"));
const Updates = lazy(() => import("@/pages/Updates"));
const Search = lazy(() => import("@/pages/Search"));
const ForgotPassword = lazy(() => import("@/pages/ForgotPassword"));
const ResetPassword = lazy(() => import("@/pages/ResetPassword"));
const VerifyEmail = lazy(() => import("@/pages/VerifyEmail"));
const Legal = lazy(() => import("@/pages/Legal"));
const Admin = lazy(() => import("@/pages/Admin"));
const NotFound = lazy(() => import("@/pages/NotFound"));

// One <Route> per page in src/pages; BrowserRouter already wraps this in main.tsx.
export default function App() {
  return (
    <Suspense fallback={<div role="status" className="px-4 py-12 text-center text-sm">Loading page…</div>}>
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/about" element={<About />} />
        <Route path="/founders" element={<Founders />} />
        <Route path="/services" element={<Services />} />
        <Route path="/calculators" element={<Calculators />} />
        <Route path="/careers" element={<Careers />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/portal" element={<Portal />} />
        <Route path="/partner-portal" element={<PartnerPortal />} />
        <Route path="/partners" element={<Partners />} />
        <Route path="/rates" element={<Rates />} />
        <Route path="/updates" element={<Updates />} />
        <Route path="/search" element={<Search />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/how-it-works" element={<HowItWorks />} />
        <Route path="/resources" element={<Resources />} />
        <Route path="/blog" element={<Blog />} />
        <Route path="/blog/:slug" element={<BlogPost />} />
        <Route path="/faqs" element={<Faq />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/disclaimer" element={<Legal kind="disclaimer" />} />
        <Route path="/privacy" element={<Legal kind="privacy" />} />
        <Route path="/terms" element={<Legal kind="terms" />} />
        <Route path="/grievance" element={<Legal kind="grievance" />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
    </Suspense>
  );
}
