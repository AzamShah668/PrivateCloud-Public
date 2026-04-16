import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "motion/react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import { registerSchema, type RegisterValues } from "@/schemas/auth.schema";
import { register as registerApi, login } from "@/api/auth";
import { useAuthStore } from "@/stores/auth-store";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { UserPlus } from "lucide-react";
import { useState } from "react";

export default function RegisterForm() {
  const navigate = useNavigate();
  const authLogin = useAuthStore((s) => s.login);
  const [loading, setLoading] = useState(false);

  const {
    register: reg,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (values: RegisterValues) => {
    setLoading(true);
    try {
      await registerApi(values.username, values.password);
    } catch (err: unknown) {
      // Parse the actual backend error (FastAPI returns { detail: "..." })
      let message = "Registration failed. Please try again.";
      if (err && typeof err === "object" && "response" in err) {
        try {
          const body = await (err as { response: Response }).response.json();
          if (body?.detail) message = body.detail;
        } catch {
          // response wasn't JSON — keep generic message
        }
      }
      toast.error(message);
      setLoading(false);
      return;
    }

    // Registration succeeded — now try auto-login
    try {
      const res = await login(values.username, values.password);
      authLogin(res.access_token);
      toast.success("Account created! Welcome aboard.");
      navigate("/", { replace: true });
    } catch {
      // Account was created but auto-login failed
      toast.success("Account created! Please sign in.");
      navigate("/login", { replace: true });
    } finally {
      setLoading(false);
    }
  };

  const stagger = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 } };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5">
      <motion.div {...stagger} transition={{ delay: 0.9, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}>
        <Input
          label="Username"
          placeholder="Choose a username"
          autoComplete="username"
          autoFocus
          error={errors.username?.message}
          {...reg("username")}
        />
      </motion.div>

      <motion.div {...stagger} transition={{ delay: 1.05, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}>
        <Input
          label="Password"
          type="password"
          placeholder="At least 8 characters"
          autoComplete="new-password"
          error={errors.password?.message}
          {...reg("password")}
        />
      </motion.div>

      <motion.div {...stagger} transition={{ delay: 1.2, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}>
        <Input
          label="Confirm Password"
          type="password"
          placeholder="Re-enter your password"
          autoComplete="new-password"
          error={errors.confirmPassword?.message}
          {...reg("confirmPassword")}
        />
      </motion.div>

      <motion.div {...stagger} transition={{ delay: 1.35, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}>
        <Button type="submit" loading={loading} className="w-full mt-2" size="lg">
          <UserPlus className="h-4 w-4" />
          Create Account
        </Button>
      </motion.div>

      <motion.p
        {...stagger}
        transition={{ delay: 1.5, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
        className="text-center text-sm text-secondary"
      >
        Already have an account?{" "}
        <Link
          to="/login"
          className="text-accent-blue hover:underline transition-colors"
        >
          Sign in
        </Link>
      </motion.p>
    </form>
  );
}
