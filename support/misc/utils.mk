# Copyright (C) Intelli4u

_quota := "

define normalize-path
$(_quota)$(strip $(subst ",,$(1)))$(_quota)
endef

# Reverse the orders of words in a list. Again, inspired by the gmsl
# 'reverse' macro.
reverse = $(if $(1),$(call reverse,$(wordlist 2,$(words $(1)),$(1))) $(firstword $(1)))

