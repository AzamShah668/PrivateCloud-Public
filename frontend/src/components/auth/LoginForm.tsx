import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "motion/react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import { HTTPError } from "ky";
import { loginSchema, type LoginValues } from "@/schemas/auth.schema";
import { login } from "@/api/auth";
import { useAuthStore } from "@/stores/auth-store";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { LogIn } from "lucide-react";
import { useState } from "react";

export default function LoginForm() {
  const navigate = useNavigate();
  const authLogin = useAuthStore((s) => s.login);
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (values: LoginValues) => {
    setLoading(true);
    try {
      const res = await login(values.username, values.password);
      authLogin(res.access_token);
      toast.success("Welcome back");
      navigate("/", { replace: true });
    } catch (err: unknown) {
      let message = "Invalid username or password";
      if (err instanceof HTTPError) {
        try {
          const body = (await err.response.clone().json()) as { detail?: string };
          if (err.response.status === 503) {
            message = body.detail ?? "The platform is currently in maintenance mode. Please try again later.";
          } else if (body.detail) {
            message = body.detail;
          }
        } catch {
          // fall through with default message
        }
      }
      toast.error(message);
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
          placeholder="Enter your username"
          autoComplete="username"
          autoFocus
          error={errors.username?.message}
          {...register("username")}
        />
      </motion.div>

      <motion.div {...stagger} transition={{ delay: 1.1, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}>
        <Input
          label="Password"
          type="password"
          placeholder="Enter your password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...register("password")}
        />
      </motion.div>

      <motion.div {...stagger} transition={{ delay: 1.3, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}>
        <Button type="submit" loading={loading} className="w-full mt-2" size="lg">
          <LogIn className="h-4 w-4" />
          Sign In
        </Button>
      </motion.div>

      <motion.p
        {...stagger}
        transition={{ delay: 1.5, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
        className="text-center text-sm text-secondary"
      >
        Don&apos;t have an account?{" "}
        <Link
          to="/register"
          className="text-accent-blue hover:underline transition-colors"
        >
          Register
        </Link>
      </motion.p>
    </form>
  );
}
