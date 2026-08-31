# Exactly-once Instagram publishing

Scheduled and manual publishing must never post the same job twice. A job is claimed before the external call and any uncertain result enters `Publicação incerta`, blocking retries until the user confirms it was published or discards the attempt.
