CREATE OR REPLACE FUNCTION public.bump_version()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  UPDATE public.account
  SET version = version + 1
  WHERE id = NEW.id;
  RETURN NEW;
END;
$$;

