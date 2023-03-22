variable "add_policy" {
  type = string
  default = <<EOF
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Action": "sts:AssumeRole",
          "Effect": "Allow",
          "Principal": {
            "Service": "lambda.amazonaws.com"
          }
        }
      ]
    }
  EOF
}

variable "source_dir" {
  default = "source"
}

variable "output_dir" {
  default = "data"
}

variable "region" {
  default = "eu-central-1"
}
