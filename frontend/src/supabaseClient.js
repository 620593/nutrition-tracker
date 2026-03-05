/*
 * This file creates and exports a configured Supabase client instance for the frontend.
 * It reads the project URL and public anon key from Vite environment variables prefixed
 * with VITE_ and initializes the Supabase JS client with those credentials.
 * When fully implemented, it will be imported by the auth context, the API client
 * interceptor, and any page that needs to interact directly with Supabase Auth or
 * Realtime subscriptions.
 */

import { createClient } from "@supabase/supabase-js";

const supabaseUrl =
  import.meta.env.VITE_SUPABASE_URL || "https://your-project.supabase.co";
const supabaseAnonKey =
  import.meta.env.VITE_SUPABASE_ANON_KEY || "your-anon-key";

const supabase = createClient(supabaseUrl, supabaseAnonKey);

export default supabase;
